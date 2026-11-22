# Acceptance and verification status

## Current source-level acceptance

The frontend unit and HTTP suites check that:

- the root route always renders the single-chat shell;
- legacy customer routes and demo pages are absent;
- chat API paths and query parameters are allowlisted;
- mutations require same-origin requests and server-side authentication;
- the internal request-details card uses a conversation-scoped frontend endpoint;
- production does not enable the isolated agent transport.

The synthetic browser acceptance mounts the actual `SingleChatWorkspace`, sends a message through the real FastAPI conversation API, verifies persistence/resumption, and confirms a second signed synthetic owner receives no access. The backend suite checks typed conversation contracts, ownership, resumption, approval revisions, source provenance and deterministic applicability. PostgreSQL-backed integration checks use disposable databases.

## Environment boundaries

| Environment | Current status |
| --- | --- |
| Local development | Chat UI and explicitly configured local services can be exercised. |
| Isolated Preview | Agent transport is available only under the reviewed branch, database fingerprint, identity and encryption-key gates. |
| Production | Chat shell may be served, but agent transport/worker execution is disabled. No production assistant readiness is claimed. |

## Not established

- Live participant outcomes or broad user research.
- Current legal correctness for every Italian municipality or personal circumstance.
- Production agent execution, model quality or hosted worker reliability.
- Real personal-document upload, malware scanning, OCR or document retention.
- Production end-to-end two-account conversation isolation after the UI migration.
- Government eligibility, submission or confirmation.

A green automated test, merged PR or frontend deployment is not a substitute for these checks.
