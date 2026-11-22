# Conversation wire examples

The synthetic typed examples used by the Phase 4 agent contract tests live in [agent_wire_examples.json](../../backend/tests/fixtures/agent_wire_examples.json).

The fixture covers message acceptance, active-run discovery, persisted questions, replies, source cards, approval snapshots and write receipts. It contains only fictional identifiers and URLs. The test validates each example against the corresponding Pydantic model and checks the cross-event revision and provenance invariants.

These examples are contract fixtures, not a Phase 5 implementation plan or evidence of production deployment.
