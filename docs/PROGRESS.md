# Progress

Task 30. Written on 2 November 2026. The backlog is [TASKS.yaml](TASKS.yaml). The decisions are in [DECISIONS.md](DECISIONS.md).

The status of a task is its row in the backlog. The next task is whatever `py -3 scripts/check_tasks.py` prints. This file is not a rule the agent may state.

## Blockers

These stay open when the next task advances.

- The design direction from task 20 is not approved.
- The controls in [SECURITY.md](architecture/SECURITY.md) and the choices in [API.md](architecture/API.md) are unreviewed. Do not build the server from them.
- The research rows are unreviewed. Do not state a document, a deadline, or an eligibility rule from them.

## Update

Set a task to `done` and its verification to `artifact on main` only after that task's check passed. If `approval` is `user`, write `accepted: <id>` in [DECISIONS.md](DECISIONS.md) first. Then run the checker again. The printed id is the next task.
