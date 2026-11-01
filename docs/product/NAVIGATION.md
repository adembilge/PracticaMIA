# Navigation

Task 18. Written on 2 November 2026. The journeys are in [JOURNEYS.md](JOURNEYS.md). The fields are in [INTAKE.md](INTAKE.md).

This file is the page map and the low-fidelity frames. It is not a visual design, and it is not a rule the agent may state. Error, retry, and session-expired screens stay in Task 19.

An excluded story stops in chat. U-01, U-02, and U-03 do not open a case, so the case routes do not appear.

## Sitemap

| Screen | Route | What it shows |
|---|---|---|
| Dashboard | The start | Nothing, or the one open case and its stop: not ready, or ready to hand over |
| AI chat | From the dashboard, and from the case | The message thread and the one question still missing |
| Case details | From the dashboard, when a case is open | The stop, and the links to chat, documents, checklist, and application review |
| Documents | From the case | The title paper, and the identity or permit paper when the intake requires it |
| Checklist | From the case | The missing fields from the intake. Not the unreviewed document catalog |
| Application review | From the case | The package and the CH-01 address when ready to hand over. Otherwise the not-ready reason |

Documents, checklist, and application review open from the case without a chat message. Application review does not contain a password field.

## Desktop

Each frame has a side list of the five case routes, then the one block that screen holds. The side list is Case, Chat, Documents, Checklist, Review. The dashboard has no side list, because there may be no case yet.

```
Dashboard
+------------------+
| No open case     |
| or               |
| One case         |
| not ready        |
| or ready to hand |
| over             |
+------------------+
```

```
Case details
+----------+------------------+
| Case     | Stop             |
| Chat     | not ready, or    |
| Documents| ready to hand    |
| Checklist| over             |
| Review   |                  |
+----------+------------------+
```

```
AI chat
+----------+------------------+
| Case     | Message thread   |
| Chat     | One missing      |
| Documents| question         |
| Checklist|                  |
| Review   |                  |
+----------+------------------+
```

```
Documents
+----------+------------------+
| Case     | Title paper      |
| Chat     | Identity or      |
| Documents| permit paper     |
| Checklist|                  |
| Review   |                  |
+----------+------------------+
```

```
Checklist
+----------+------------------+
| Case     | Missing fields   |
| Chat     | from the intake  |
| Documents|                  |
| Checklist|                  |
| Review   |                  |
+----------+------------------+
```

```
Application review
+----------+------------------+
| Case     | Package and the  |
| Chat     | CH-01 address    |
| Documents| or the not-ready |
| Checklist| reason           |
| Review   |                  |
+----------+------------------+
```

When the case is not ready, application review shows the missing title paper, or the two values on a mismatch. It shows the package and the CH-01 address only when the case is ready to hand over.

## Mobile

The same blocks stand in one column. The side list becomes a top list. Every screen uses that list. The six frames are not redrawn.

```
Mobile
+------------------+
| Case | Chat      |
| Documents        |
| Checklist        |
| Review           |
+------------------+
| The one block    |
| for this screen  |
+------------------+
```

The dashboard stays a single block, with no list until a case exists.

## Actions without chat

- Documents uploads the title paper, and the identity or permit paper when the intake requires it.
- Checklist shows the missing field.
- Application review shows the CH-01 address only when the case is ready to hand over.
- Return opens the dashboard, then the same case.
