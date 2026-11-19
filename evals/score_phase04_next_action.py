"""Replay synthetic development cases and score the next action visible to the user."""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import CheckpointState, submit_clarification_reply
from app.agent.contract import (
    AnswerResult, ClarificationReply, EvidenceLinkedClaim, NextAction, OfficialChannel,
    QuestionRequested, SendMessage,
)
from app.agent.intent_extraction import identify_intent_step
from app.agent.run_events import read_run_events, read_run_snapshot
from app.agent.run_handoff import read_run_handoff
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import run_worker_step
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base
from app.knowledge.review_service import revoke_version
from app.knowledge.search import resolve_approved_passage
from app.rules.approval import has_valid_human_review_signature
from app.rules.engine import PROCEDURE, evaluate_condition, load_catalog

from score_phase04_agent import ALIASES, DATASET, NAMES, SYNTHETIC_REVIEWER, _evidence_fixtures, _locations


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend/app/rules/catalog.json"
REVIEW_KEY = ROOT / "requirements/milan-residence-change/review_public_key_v1.b64"
LABELS = {name.catalogue_id: name.display_name for name in NAMES}


@dataclass(frozen=True)
class Observation:
    action: str | None = None
    fields: tuple[str, ...] = ()
    authorities: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    selected_procedure: str | None = None
    question: bool = False
    channel: bool = False
    verified: bool = False
    blocked: str | None = None


class ScenarioReplay:
    def __init__(self, sessions, data, case, language, catalog):
        self.sessions = sessions
        self.references = data["references"]
        self.facts = data["profiles"].get(case.get("initial_profile"), {}) | case.get("initial_facts", {})
        self.language = language
        self.route_conditions = [rule["condition"] for rule in catalog["rules"] if rule["kind"] == "route"]
        self.case_id = uuid4() if case.get("initial_profile") else None
        self.snapshot = None
        self.question_boundaries = {}
        self.context = {"principal": Principal("phase04-next-action"), "key": bytes(range(32))}
        with sessions.begin() as db:
            self.evidence = _evidence_fixtures(db, data)
            thread = create_thread(db, principal=self.context["principal"])
            if self.case_id is not None:
                db.add(CaseRecord(id=str(self.case_id), owner_subject=self.context["principal"].subject))
                db.flush()
                link_case_to_thread(db, thread_id=thread, case_id=self.case_id, principal=self.context["principal"])
        self.context["thread_id"] = thread

        # The fixture connects authority and channel claims to reviewed rule references.
        # The URLs and statements in this registry exist only within the evaluation.
        [receiving_office] = [
            item for item in self.evidence if self.references[item.reference]["role"] == "receives_application"
        ]
        rule_id = self.references[receiving_office.reference]["signed_evidence"]["rule_id"]
        rule = next(rule for rule in catalog["rules"] if rule["id"] == rule_id)
        self.channel_condition = rule["condition"]
        self.channel_passages = [item for item in self.evidence if item.pinned_passage in rule["evidence_refs"]]
        self.channel = OfficialChannel(
            label=self.references[receiving_office.reference]["authority_label"],
            url=receiving_office.citation.official_url,
        )
        statement = "Synthetic receiving office and filing channel for this replay."
        self.channel_review = ReviewedClaimSupport(
            kind="channel", language=language, statement=statement, official_channel=self.channel,
            passages=tuple(
                ClaimPassageSupport(item.citation.passage_id, item.assignment.assignment_id, item.text)
                for item in self.channel_passages
            ),
        )

    def read_scope(self, *_):
        return AnswerEvidenceScope(
            procedure_id=PROCEDURE,
            case_locations=_locations(self.facts),
            confirmed_dates={}, confirmed_circumstances={},
            assignments=tuple(item.assignment for item in self.evidence),
            claim_reviews=(self.channel_review,),
        )

    def execute(self, message, state):
        if state.next_node == "load_context":
            return CheckpointState(next_node="identify_intent")
        if state.next_node == "identify_intent":
            return identify_intent_step(message, state, catalogue_names=NAMES)
        if state.next_node == "choose_next_step":
            scope = self.read_scope()
            with self.sessions() as db:
                trusted = frozenset(
                    item.citation.passage_id for item in self.evidence
                    if resolve_approved_passage(
                        db, citation_id=item.citation.passage_id, jurisdiction=item.citation.location_id,
                        procedure_id=item.citation.procedure_id, language=None,
                    ) is not None
                )
            return choose_candidate_step(
                message, state, case_locations=scope.case_locations, confirmed_dates=scope.confirmed_dates,
                confirmed_circumstances=scope.confirmed_circumstances, assignments=scope.assignments,
                trusted_passage_ids=trusted, reviewed_labels=LABELS, catalogue_names=NAMES,
            )

        # This adapter supplies a draft for the isolated worker's publication boundary.
        # It reads the signed conditions and actual routing state, without reading gold outcomes.
        if (
            state.procedure_candidates != [PROCEDURE]
            or not any(evaluate_condition(condition, self.facts)[0] == "TRUE" for condition in self.route_conditions)
            or evaluate_condition(self.channel_condition, self.facts)[0] != "TRUE"
        ):
            text = "The replay has no applicable reviewed route." if self.language == "en" else (
                "La simulazione non ha una procedura verificata applicabile."
            )
            return AnswerResult(explanation=text, verification_status="insufficient_evidence")
        citations = [item.citation for item in self.channel_passages]
        return AnswerResult(
            explanation=self.channel_review.statement, verification_status="verified", citations=citations,
            official_channel=self.channel,
            next_action=NextAction(label=self.channel.label, operation="open_official_channel"),
            claims=[EvidenceLinkedClaim(
                kind="channel", statement=self.channel_review.statement,
                evidence_ids=[citation.passage_id for citation in citations],
            )],
        )

    def read_question(self):
        if self.snapshot is None or self.snapshot.status != "waiting_for_information":
            return None
        with self.sessions() as db:
            page = read_run_events(db, **self.context, after_seq=self.snapshot.last_event_seq - 1)
        [event] = page.events
        if not isinstance(event, QuestionRequested):
            raise RuntimeError("The pending question must be the current event")
        return event.question

    def observe(self, *, restored=False, current_only=False):
        question = self.read_question()
        if question is not None:
            fields = tuple(sorted(
                "destination_municipality" if field == "destination" else field for field in question.missing_fields
            ))
            action = "choose_active_goal" if question.goal_selection_language else "provide_information"
            return Observation(action=action, fields=fields, question=not restored and not current_only)
        if self.snapshot is None or self.snapshot.result is None:
            return Observation()

        result = self.snapshot.result
        with self.sessions() as db:
            handoff = read_run_handoff(
                db, self.snapshot, principal=self.context["principal"], key=self.context["key"],
                read_evidence_scope=self.read_scope,
            )
        action = result.next_action.operation if result.next_action else None
        channel = result.official_channel
        ids = [] if current_only else [citation.passage_id for citation in result.citations]
        if handoff is not None:
            if handoff.status == "verification_required":
                action = "revalidate_sources"
            else:
                action = handoff.next_action.operation
            channel = handoff.official_channel
            if current_only:
                ids = handoff.evidence_ids

        pinned_by_id = {item.citation.passage_id: item.pinned_passage for item in self.evidence}
        citations = tuple(sorted(pinned_by_id.get(item, "unmapped_passage") for item in ids))
        authorities = {
            self.references[item.reference]["authority_id"] for item in self.evidence
            if "authority_id" in self.references[item.reference] and channel is not None
            and item.citation.official_url == channel.url
        }
        active = result.goal_selection.active_goal if result.goal_selection else None
        procedures = result.goals[active - 1].procedure_candidates if active else []
        return Observation(
            action=action, authorities=tuple(sorted(authorities)), citations=citations,
            selected_procedure=procedures[0] if len(procedures) == 1 else None, channel=channel is not None,
            verified=result.verification_status == "verified" and channel is not None,
        )

    def advance(self):
        for _ in range(6):
            self.snapshot = run_worker_step(
                self.sessions, **self.context, execute=self.execute, read_evidence_scope=self.read_scope,
            )
            if self.snapshot is None:
                return Observation(blocked="run_unavailable")
            if self.snapshot.status not in {"queued", "running"}:
                return self.observe()
        return Observation(blocked="worker_step_budget")

    def step(self, step, *, question_was_aligned):
        event = step["event"]
        if event == "source_change":
            with self.sessions.begin() as db:
                for item in self.evidence:
                    if item.reference == step["withdrawn_ref"]:
                        revoke_version(
                            db, version_id=str(item.citation.source_version_id), expected_digest=item.digest,
                            actor_subject=SYNTHETIC_REVIEWER, reason="Disposable source withdrawal",
                        )
            return self.observe(current_only=True)

        if event == "message":
            message = SendMessage(
                client_message_id=uuid4(), case_id=self.case_id,
                text=step["text"][self.language], language=self.language,
            )
            request_context = {key: self.context[key] for key in ("thread_id", "principal", "key")}
            with self.sessions.begin() as db:
                accepted = accept_message(db, **request_context, message=message)
            if accepted.outcome != "accepted":
                return Observation(blocked=accepted.outcome)
            self.context["run_id"] = accepted.run_id
            self.facts.update(step.get("facts", {}))
            observation = self.advance()
            if (question := self.read_question()) is not None:
                self.question_boundaries[step["id"]] = (question.question_id, self.snapshot.run_revision)
            return observation

        prior = self.question_boundaries.get(step["question_step"])
        question = self.read_question()
        if question is None or prior != (question.question_id, self.snapshot.run_revision):
            return Observation(blocked="required_question_missing")
        if not question_was_aligned:
            return Observation(blocked="required_question_mismatch")
        if event == "reopen":
            with self.sessions() as db:
                self.snapshot = read_run_snapshot(db, **self.context)
            restored = self.read_question()
            if restored is None or prior != (restored.question_id, self.snapshot.run_revision):
                return Observation(blocked="question_not_restored")
            return self.observe(restored=True)

        text = step["text"][self.language]
        if procedure := step.get("selected_procedure_id"):
            label = ALIASES[procedure][0]
            choices = [
                option for option in question.options
                if option.partition(". ")[2].split(" · ", 1)[0] == label
            ]
            if len(choices) != 1 or question.goal_selection_language is None:
                return Observation(blocked="requested_choice_unavailable")
            [text] = choices
        reply = ClarificationReply(
            client_reply_id=uuid4(), expected_run_revision=self.snapshot.run_revision, text=text,
        )
        with self.sessions.begin() as db:
            submit_clarification_reply(
                db, **self.context, question_id=question.question_id, reply=reply,
            )
        return self.advance()


def score_case(replay, case, references):
    rows = {}
    uncorrected_misrouting = False
    for step in case["steps"]:
        expected = step["expect"]
        fields = tuple(sorted(expected.get("fields", [])))
        authorities = tuple(sorted(expected.get("authority_ids", [])))
        citations = tuple(sorted(
            passage for ref in expected.get("citation_refs", [])
            for passage in references[ref]["signed_evidence"]["passage_ids"]
        ))
        question_step = step.get("question_step")
        observed = replay.step(step, question_was_aligned=question_step is None or rows[question_step]["passed"])
        authority_correct = None
        if authorities:
            authority_correct = observed.verified and observed.authorities == authorities
        misrouted = observed.channel and (not authorities or observed.authorities != authorities)
        unnecessary = observed.question and bool(set(observed.fields).difference(fields))
        next_action_correct = (
            observed.blocked is None and observed.action == expected["next_action"] and observed.fields == fields
            and (not authorities or authority_correct is True)
            and observed.citations == citations and not misrouted
            and observed.selected_procedure == step.get("selected_procedure_id")
        )
        if misrouted:
            uncorrected_misrouting = True
        elif next_action_correct and (
            observed.verified or observed.action in {"revalidate_sources", "reassess_destination", "verify_filing_channel"}
        ):
            uncorrected_misrouting = False
        rows[step["id"]] = {
            "id": step["id"], "passed": next_action_correct,
            "expected": {
                "action": expected["next_action"], "fields": fields,
                "authorities": authorities, "citations": citations,
                "selected_procedure": step.get("selected_procedure_id"),
            },
            "observed": {
                "action": observed.action, "fields": observed.fields,
                "authorities": observed.authorities, "citations": observed.citations,
                "selected_procedure": observed.selected_procedure, "blocked": observed.blocked,
                "new_question": observed.question, "official_channel": observed.channel,
            },
            "authority_correct": authority_correct,
            "supported_citations": len(set(observed.citations).intersection(citations)),
            "unnecessary_question": unnecessary,
            "misrouted": misrouted,
        }
    return {
        "id": f"{case['id']}:{replay.language}", "language": replay.language,
        "passed": all(row["passed"] for row in rows.values()),
        "uncorrected_misrouting": uncorrected_misrouting, "turns": list(rows.values()),
    }


def run():
    raw = DATASET.read_bytes()
    data = json.loads(raw)
    catalog = load_catalog(CATALOG.read_text(encoding="utf-8"))
    if not has_valid_human_review_signature(catalog, REVIEW_KEY.read_text(encoding="utf-8").strip()):
        raise ValueError("The replay requires the signed Milan catalogue")

    cases = []
    for case in data["cases"]:
        for language in data["languages"]:
            engine = create_engine("sqlite+pysqlite:///:memory:")
            try:
                Base.metadata.create_all(engine)
                replay = ScenarioReplay(sessionmaker(bind=engine), data, case, language, catalog)
                cases.append(score_case(replay, case, data["references"]))
            finally:
                engine.dispose()

    turns = [turn for case in cases for turn in case["turns"]]
    passed = sum(case["passed"] for case in cases)
    return {
        "dataset_id": data["dataset_id"], "dataset_sha256": sha256(raw).hexdigest(),
        "mode": "offline_synthetic_conversation_replay",
        "unassisted_next_action": {"passed": passed, "total": len(cases), "pass_rate": round(passed / len(cases), 4)},
        "diagnostics": {
            "correct_turns": sum(turn["passed"] for turn in turns),
            "total_turns": len(turns),
            "correct_authorities": sum(turn["authority_correct"] is True for turn in turns),
            "required_authorities": sum(turn["authority_correct"] is not None for turn in turns),
            "supported_citations": sum(turn["supported_citations"] for turn in turns),
            "emitted_citations": sum(len(turn["observed"]["citations"]) for turn in turns),
            "required_citations": sum(len(turn["expected"]["citations"]) for turn in turns),
            "unnecessary_questions": sum(turn["unnecessary_question"] for turn in turns),
            "emitted_questions": sum(turn["observed"]["new_question"] for turn in turns),
            "official_channel_turns": sum(turn["observed"]["official_channel"] for turn in turns),
            "uncorrected_misrouting": sum(case["uncorrected_misrouting"] for case in cases),
        },
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
