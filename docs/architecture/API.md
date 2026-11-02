# API contract

Task 27. Written on 2 November 2026. The screens are in [NAVIGATION.md](../product/NAVIGATION.md). The messages are in [ERRORS.md](../product/ERRORS.md). The limits are in [SECURITY.md](SECURITY.md).

This file is the calls and the choices. It is not a server, and it is not a rule the agent may state. The choices below are unreviewed.

The browser talks only to Next.js. Next.js talks only to FastAPI. The model is not a public call. One person reads only their own case. There is one case, so nothing is paginated.

## Calls

- Read the case. Dashboard, case details, checklist, and application review. The body is nothing, or the stop, the missing field, the uploads, and the package. The CH-01 link is present only when the stop is ready to hand over.
- Send a message. AI chat. One synchronous turn. The response is the reply and the stop. An excluded story returns no case.
- Upload one file. Documents. The role is the title paper or the identity paper. The response is failed, unreadable, or read. A read carries the name and the address. Over 10 MB, an empty file, or any other type is E-01.
- Name the value. Application review, only when two readings differ. The body is the name and the address the person chose. The schema does not choose.
- Delete the person. This removes the case, the messages, the uploads, the session, the audit, and the files. It has no screen.

An error body is one code and the message already written for that row: E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-08. A second case, a credential, or a model write of the stop is refused, and the stored stop stays.

## Choices

The alternative not taken is AWS, a queue, and object storage.

- One API process and PostgreSQL. Files stay on that process.
- No account sign-in here. The person id is opaque. The credential stays on ANPR.
- FastAPI writes the stop. The model does not.
