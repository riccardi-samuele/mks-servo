<!--
Thanks for the PR! A few things to make review fast:

- Title uses Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- One logical change per PR; small PRs get merged faster
- See CONTRIBUTING.md for the full checklist
-->

## What this PR does

<!-- One or two sentences. The "why" matters more than the "what". -->

## Type of change

- [ ] Bug fix (`fix:`)
- [ ] New feature (`feat:`)
- [ ] Refactor with no behavior change (`refactor:`)
- [ ] Tests only (`test:`)
- [ ] Docs only (`docs:`)
- [ ] Chore / build / CI (`chore:`)

## Testing

- [ ] `pytest -q` passes locally
- [ ] Added/updated tests for the change
- [ ] Touched motion / transport / bus code → ran `pytest -m hil` on a real rig

<!--
If you ran HIL, paste the relevant output here (PASS/FAIL counts is enough).
If you couldn't run HIL but should have, say why.
-->

## Changelog

- [ ] Added an entry under `## [Unreleased]` in `CHANGELOG.md` (skip if no user-visible change)

## Linked issues

<!-- "Closes #123" / "Refs #456" -->
