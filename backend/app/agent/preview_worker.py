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

from app.agent.chat_graph import build_chat_executor
from app.agent.preview_mount import validate_agent_preview_settings
from app.agent.worker import run_worker_batch
from app.config import Settings

MAX_STEPS_PER_INVOCATION = 20
LEASE_SECONDS = 120

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
        execute = build_chat_executor(api.state.session_factory)
        return run_worker_batch(
            api.state.session_factory, key=key,
            lease_for=timedelta(seconds=LEASE_SECONDS),
            execute=execute, max_steps=max_steps, unlinked_only=True,
        )
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated, one-shot, case-free LangGraph chat worker")
    parser.add_argument("--once", action="store_true", help="Execute one bounded batch and exit")
    parser.add_argument("--unverified-only", action="store_true",
                        help="Acknowledge no verified guidance or LLM is available")
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args(argv)
    if not (args.once and args.unverified_only):
        parser.error("Explicit --once --unverified-only consent is required")
    # Never print prompts, owner IDs, connection strings, plaintext content or keys.
    count = run_preview_worker_once(Settings.from_env(), max_steps=args.max_steps)
    print(f"Phase 4 chat worker committed {count} step(s); references remain non-personalized and unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
