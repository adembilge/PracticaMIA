"""One bounded Phase 4 agent worker invocation for an isolated Preview only.

This module is intentionally NOT an autonomous scheduler or an LLM executor.
It uses existing durable lease/checkpoint fencing. Until an independently
reviewed official-source execution adapter is approved, it can produce only
an explicitly *unverified* no-guidance response. No writes to case facts,
documents, external portals or human-review records are performed.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from typing import Sequence

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult
from app.agent.intent_extraction import identify_intent_step
from app.agent.preview_mount import validate_agent_preview_settings
from app.agent.run_requests import StoredMessage
from app.agent.worker import run_worker_batch
from app.config import Settings

MAX_STEPS_PER_INVOCATION = 20
LEASE_SECONDS = 120

_NO_GUIDANCE = {
    "en": (
        "Your message was saved, but this Preview cannot yet give a verified "
        "administrative answer from reviewed official sources. No government "
        "application has been filed and no personal details have been changed."
    ),
    "it": (
        "Il tuo messaggio è stato salvato, ma questa anteprima non può ancora "
        "fornire una risposta amministrativa verificata da fonti ufficiali "
        "revisionate. Nessuna domanda è stata inviata e nessun dato personale "
        "è stato modificato."
    ),
}


def preview_unverified_step(message: StoredMessage, state: CheckpointState):
    """Advance safely without claiming source review or using an LLM.

    This is a temporary diagnostic mode, NOT the final agent logic. Intent
    extraction is an offline, tentative routing hint only; its output never
    becomes verified guidance in this adapter.
    """
    if state.next_node == "load_context":
        return CheckpointState(next_node="identify_intent")
    if state.next_node == "identify_intent":
        return identify_intent_step(message, state, catalogue_names=())
    if state.next_node in {"choose_next_step", "find_evidence", "verify_and_respond"}:
        return AnswerResult(
            explanation=_NO_GUIDANCE[message.language],
            verification_status="insufficient_evidence",
        )
    raise ValueError("Unexpected worker checkpoint node")


def run_preview_worker_once(settings: Settings, *, max_steps: int) -> int:
    """Use the mounted API's exact schema/identity/config checks and same DB.

    This call is *not* scheduled by Vercel and cannot run in production.
    """
    if not 1 <= max_steps <= MAX_STEPS_PER_INVOCATION:
        raise ValueError("Worker must have a strictly bounded step budget")
    key = validate_agent_preview_settings(settings)
    if key is None:
        raise ValueError("Worker requires explicitly enabled isolated agent Preview")
    from app.main import create_app

    api = create_app(settings)
    engine = api.state.engine
    try:
        return run_worker_batch(
            api.state.session_factory, key=key,
            lease_for=timedelta(seconds=LEASE_SECONDS),
            execute=preview_unverified_step, max_steps=max_steps,
        )
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated, one-shot, unverified-only agent worker")
    parser.add_argument("--once", action="store_true", help="Execute one bounded batch and exit")
    parser.add_argument("--unverified-only", action="store_true",
                        help="Acknowledge no verified guidance or LLM is available")
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args(argv)
    if not (args.once and args.unverified_only):
        parser.error("Explicit --once --unverified-only consent is required")
    # Never print prompts, owner IDs, connection strings, plaintext content or keys.
    count = run_preview_worker_once(Settings.from_env(), max_steps=args.max_steps)
    print(f"Phase 4 isolated worker committed {count} step(s); all answers remain unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
