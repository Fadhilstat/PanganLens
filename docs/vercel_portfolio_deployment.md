# Vercel static portfolio delivery

## Source and build

- Canonical source: https://github.com/Fadhilstat/PanganLens
- GitLab mirrors source and remains a CI/Pages fallback. No VPS or runtime cloud keys.
- Static output is the checked `website/` directory with an intentionally empty public price snapshot until a separately reviewed publication.
- Vercel project root: `website`; framework: Other/static; output directory: `.`; no install/build command.
- Production target: https://panganlens-portfolio.vercel.app/
- Do not advertise the host until a successful production deployment and unauthenticated HTTP check confirm it.

## Access and release safety

Vercel GitHub integration for the canonical repository must be installed to enable automatic Git push deploys. An initial repository link attempt returned an integration-required error. Do not alter the existing `panganlens-indonesia` Vercel project since it belongs to a different repository.

For protected previews, a login prompt is not proof of public availability. Production domain must be independently checked in a logged-out session. Check HTML, stylesheet, scripts, dashboard JSON and calculator. Verify that the dashboard remains empty when the checked snapshot is empty.

## Rollback

Vercel deployment history supports return to a previously verified release. Never roll back to a build with fake prices or an unreviewed publication state. GitHub `main` remains the canonical code source.
