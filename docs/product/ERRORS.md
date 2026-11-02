# Errors and recovery

Task 19. Written on 2 November 2026. The screens are in [NAVIGATION.md](NAVIGATION.md). The replies are in [CONVERSATION.md](CONVERSATION.md). The fields are in [INTAKE.md](INTAKE.md).

This file is the blocked states and the recovery. It is not a visual design, and it is not a rule the agent may state. It does not add a screen. It does not say the Comune will accept the declaration.

Saving is not a separate button. The case keeps each answer and each upload. Replacing a paper on Documents, or naming the correct value on application review, runs the check again. The old mismatch is not kept once the person has replaced it.

## States

| ID | Condition | Screen | Message | Next action |
|---|---|---|---|---|
| E-01 | Upload failed | Documents | The file did not upload. | Retry the same upload. The case stays not ready. |
| E-02 | Unreadable paper | Documents | The file cannot be read. | Upload a readable copy of that same paper. Do not fill F-09 from it. |
| E-03 | Facts conflict | Application review | I-02. Show both values and ask which is correct. Do not pick. | The person names the value. The case stays not ready until then. |
| E-04 | Missing title paper | Checklist and application review | I-01. The lease or the ownership paper is missing, and her name must be on it. | Upload that paper. Do not show the CH-01 address. |
| E-05 | Sources unavailable | AI chat | This release does not state that. The question was a deadline, an unasked paper, or the only sign-in method. | Do not guess. The case, if open, stays as it was. |
| E-06 | Cannot tell the door | AI chat | After the one A-01 or A-02 question, the answer still does not classify. | Do not ask a second time. Do not open the case. Add no steps. |
| E-07 | Session expired, or the person left | Dashboard | The case is still there, including the unanswered question and the uploads. | Resume opens that case. Do not start the story again. |
| E-08 | Language | AI chat | U-03. Continue in English or Italian. | She sends the request again in English or Italian. No case until then. |

## Return

The person leaves mid-question. She comes back. The dashboard shows the same case. The missing question is still the only one asked.
