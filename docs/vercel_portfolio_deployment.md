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


## Root directory and source upload contract

- Vercel project `panganlens-portfolio` uses project root `website`.
- When deploying manually with the Vercel API from the **repository root**, upload `website/index.html`, `website/styles.css`, `website/app.js`, `website/dashboard_metrics.js`, `website/price_playground.js`, `website/data/dashboard.json` and `website/vercel.json`. These paths include the project root.
- A preview attempt with these paths *without* the `website/` prefix failed with `NOW_SANDBOX_WORKER_ROOTDIR_NOT_EXIST`. Do not change the existing production alias based on that failed preview.
- The source deploy was recorded as GitHub main SHA `c212bab109ce5d5355eb7e1716fa7c091c5938ba`. The build reached `READY`, which is not the same as public HTTP verification.
- To enable Git-based automatic deployment, the owner installs Vercel's GitHub integration with access to `Fadhilstat/PanganLens`. Then link the *new* Vercel project, not the unrelated `panganlens-indonesia` project.

## Release verification

Run the anonymous smoke from a networked CI runner:

```bash
python scripts/check_public_site.py --url https://panganlens-portfolio.vercel.app/ --attempts 3
```

The verifier requires the production HTTPS host, editorial launch markup, canonical and Open Graph URL, stylesheet, JavaScript assets and a structurally valid public snapshot. It does not use tokens. GitLab `public_site_smoke` runs on merge requests and `main` as a nonblocking public availability signal. Do not report launch-ready while it is failing. The snapshot JSON is served with `Cache-Control: no-store` from Vercel static headers.

Visual verification at 360px, 768px and desktop, including calculator submit/reset, keyboard focus and horizontal overflow, is a separate check. Mark it `NOT_RUN` until a real browser or a Playwright runner completes it.
