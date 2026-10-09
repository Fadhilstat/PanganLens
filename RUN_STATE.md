# RUN_STATE

Updated: 2026-10-10 (Asia/Jakarta)
Project: PanganLens Indonesia
Phase: 2 Technical Implementation, Phase 3 Repository/README, Phase 4 Portfolio Preview
Current milestone: Trustworthy portfolio preview with user-input calculator and static Pages
Status: RELEASE_CANDIDATE, requires live CI and Pages access verification

## Verified baseline before this milestone

- GitHub: https://github.com/Fadhilstat/PanganLens
- GitHub source main: 6a731b14c4c4944b35ee35834cff399d5e543544.
- GitLab: https://gitlab.com/fadhilrusydih/panganlens
- GitLab main before this milestone: a4cfb5fcf7cd89132af36e2e4777f31048e5baad.
- GitLab MR !1 merged; source file blob SHA parity was verified for all 149 files.
- GitLab main pipeline #2931733482: SUCCESS (previous, pre-milestone code).
- GitHub and GitLab commit SHA differs due to content-snapshot import rather than shared history.
- Public snapshot website/data/dashboard.json: empty, publish_state null.
- GCP activation from GitHub issue #48: not completed and remains independent.

## Release candidate changes

- Website: input-only positive-rupiah calculator, explicit provenance, an architecture case-study section, mobile nav, skip link, focus states and reduced motion.
- Numeric fixes: zero and missing values are not silently displayed as valid production observations.
- README: recruiter-facing product narrative, real architecture, reproducible test commands and limitations.
- Documentation: portfolio case study and Pages release procedures.
- GitHub Actions: separate built-in Node calculation test gate.
- GitLab CI: verify stages for Python and Node, default-branch-only static Pages publish after both pass.
- No new runtime dependencies, cloud credentials, GCP setup, production ingestion or VPS.

## QA evidence

- Local Node calculation tests: PASS (7 tests).
- Local JavaScript syntax check for the new calculator: PASS.
- GitHub full CI for this candidate: NOT_RUN until PR branch is pushed.
- GitLab CI and Pages pipeline for this candidate: NOT_RUN until MR and main pushes.
- Browser screenshots, GitHub Pages deploy, public GitLab Pages access: NOT_VERIFIED.
- Final GitHub/GitLab file-hash parity: NOT_VERIFIED until both changes merge.
- Full warehouse production data path: NOT_RUN and NOT_CLAIMED.

## Safety gates

- Approved: APPROVE PUSH and APPROVE MERGE for this milestone, confirmed in this chat.
- Still require reviewed diff, passing Python and Node CI, and verified MR head before each merge.
- GitLab Pages access level was private when inspected; CI deployment alone does not make the site publicly viewable.
- Keep BigQuery snapshot empty until source, mapping, warehouse and publish-state gates are verified.

NEXT_ACTION: Push a single review branch to GitHub, run quality CI, merge only on green checks, then sync the exact changed files to a GitLab MR, verify its pipeline and static Pages deployment, and inspect published URLs.
