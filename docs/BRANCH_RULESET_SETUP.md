# Main Branch GitHub Ruleset — Owner Setup

**Repository:** https://github.com/adembilge/PracticaMIA  
**Status:** Owner action required. The connected GitHub integration has no ruleset write permission.

1. Open https://github.com/adembilge/PracticaMIA/settings/rules.
2. Select **New ruleset → New branch ruleset**.
3. Name: **Protect main**. Set **Enforcement status: Active**.
4. Target: **Default branch** (`main`).
5. Enable **Require a pull request before merging**; use **0 required approvals** for a solo-maintained repository.
6. Enable **Require status checks to pass**; add **Tests, types, and build** from GitHub Actions.
7. Enable **Require branches to be up to date before merging**.
8. Keep force pushes and branch deletions blocked; use no bypass actors unless essential.
9. Save and verify that `main` is covered by an **Active** ruleset.

Vercel Preview Comments is **not** a verification that the preview site built correctly. Review the actual Vercel deployment separately.

The above controls become enforceable only after the repository owner activates them. A documented configuration alone does not protect the branch.
