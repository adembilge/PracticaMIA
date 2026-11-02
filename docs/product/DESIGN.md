# Design reference

Task 20. Written on 2 November 2026. The screens are in [NAVIGATION.md](NAVIGATION.md). The blocked states are in [ERRORS.md](ERRORS.md). [VISION.md](VISION.md) sets no visual direction.

This file is the visual reference for those screens. It is not a new screen, and it is not a rule the agent may state. The text frames are the prototypes. Stage 4 does not start from this file.

## Tokens

One text face for the interface, the same in English and Italian. Official Italian terms stay in the sentence, not in a second face.

Two space steps. The small step separates a label from its control. The large step separates the route list from the one block. Desktop is the side list plus that block. Mobile is the top list plus that block.

Color roles, by name: page, text, action, ready, not ready, blocked. The status word is always visible next to the color. A blocked state does not use the ready role.

## Components

The route list, the message, the one text question, the upload, the status line, the warning, and the CH-01 link.

The CH-01 link appears only when the case is ready to hand over. A warning uses the message already written for that E- row. The required action is the next action on that row. No component is a password field.

The one text question has a visible label. The status is a word, not a color alone. Documents, Checklist, and Application review are in the route list, so the person can open them without chat. Text can grow without hiding the next action.

## States

The question can be waiting for an answer. The upload can be waiting for a retry. The case is not ready, or ready to hand over. A blocked state does not look like ready.

## Map

| Screen | Components |
|---|---|
| Dashboard | Status line. The route list only when a case is open. |
| Case details | Route list and status line. |
| AI chat | Message and the one text question. |
| Documents | Upload and, when the upload failed or cannot be read, the warning. |
| Checklist | The missing field, and the warning when the title paper is missing. |
| Application review | Status line. The warning when not ready. The CH-01 link only when ready to hand over. |

| State | Looks like |
|---|---|
| E-01 | Documents. Warning: the file did not upload. The upload is the retry. Not ready. |
| E-02 | Documents. Warning: the file cannot be read. The upload asks for a readable copy. Not ready. |
| E-03 | Application review. Warning shows both values. Not ready. No CH-01 link. |
| E-04 | Checklist and Application review. Warning names the missing title paper. Not ready. No CH-01 link. |
| E-05 | AI chat. The message says this release does not state that. The case stays as it was. |
| E-06 | AI chat. The message says the door is still unknown. No case route. |
| E-07 | Dashboard. The status line shows the same case. Resume opens it. |
| E-08 | AI chat. The one text question asks for English or Italian. No case route. |

The direction is unreviewed until you mark it.
