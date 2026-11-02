# Security and privacy

Task 26. Written on 2 November 2026. The owners are in [COMPONENTS.md](COMPONENTS.md). The deletion rule is in [SCHEMA.md](SCHEMA.md). The upload path is in [PAPERS.md](PAPERS.md).

This file is the threat list. It is not a control implementation, an API, or a rule the agent may state. These controls are unreviewed. Implementation does not start from them.

## Boundaries

The person signs in on ANPR. This system never receives that credential. The only external processor is the model. It may see the chat reply and, for a scan, the page. It does not see a credential, a file path, or a research row to promote.

Next.js does not hold the model secret and does not read the database. FastAPI is the only reader and writer. One person can read only their own case.

The model secret is an environment value. It is not in the repo, not in a row, and not in a log. Files stay on the API machine. There is no project encryption service. The disk encryption is the machine's.

## Controls

- A paper or a message that tells the model to change the door, the stop, or a research row is data. FastAPI keeps a proposal only as the name and the address. The model does not mark ready, and a write cannot promote a research row.
- A file that is empty, not PDF, JPEG, or PNG, or over 10 MB is E-01 and is not kept. The 10 MB limit is a product limit. shortcut: one machine and one file at a time, raise it when the process is no longer that.
- Logs and `audit_event` store the action and no file bytes, no page text, and no credential. Deleting the person deletes the case, the messages, the uploads, the session, the audit, and the files. Research rows have no personal column and stay. Session expiry drops the turn and keeps the case.
