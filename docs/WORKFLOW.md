# Workflow

The next task is the id `py -3 scripts/check_tasks.py` prints. Do that work on a branch or a worktree.

A failing check leaves the row `not_started`. A row with `approval: user` stays `not_started` until `accepted: <id>` is in [DECISIONS.md](DECISIONS.md). The checker enforces that for an id after 29.

Only a passing check sets `status` to `done` and `verification` to `artifact on main`. Run the checker again. The printed id is the next task.

A later session resumes from the backlog and the checker. Chat history is not the status. `py -3 scripts/check_workflow.py` repeats the selection, the failure stops, and a fresh worktree.
