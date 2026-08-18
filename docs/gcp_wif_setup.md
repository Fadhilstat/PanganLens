# Keyless Google Cloud authentication for PanganLens

PanganLens uses GitHub Actions OpenID Connect with Google Cloud Workload Identity Federation. The repository does not require a long-lived service account JSON key.

This setup is intentionally separate from the production ingestion schedule. First verify that the trust relationship and BigQuery access work through the manual `PanganLens GCP auth smoke test` workflow. Only after that check is green should scheduled ingestion be enabled.

## Fixed GitHub identity

Use immutable GitHub identifiers in the provider condition where possible:

- repository: `Fadhilstat/PanganLens`
- repository ID: `1335081180`
- repository owner: `Fadhilstat`
- repository owner ID: `179431732`
- production branch: `refs/heads/main`

GitHub exposes `repository_id`, `repository_owner_id`, `ref`, and other repository claims in its Actions OIDC token. The Google provider should map and check those values instead of trusting repository names alone.

## Recommended Google Cloud objects

Use dedicated resources for PanganLens rather than sharing a broad deployment identity:

- workload identity pool: `panganlens-github`
- provider: `panganlens-repo`
- service account: a dedicated PanganLens ingestion service account

The service account should receive only the BigQuery permissions required by the pipeline. Do not grant Owner, Editor, or other broad project roles for convenience.

## Provider attribute mapping and condition

Create the GitHub OIDC provider with issuer `https://token.actions.githubusercontent.com/` and map at least these claims:

```text
google.subject=assertion.sub
attribute.repository_id=assertion.repository_id
attribute.repository_owner_id=assertion.repository_owner_id
attribute.ref=assertion.ref
```

Use this provider condition:

```text
attribute.repository_id == "1335081180" &&
attribute.repository_owner_id == "179431732" &&
attribute.ref == "refs/heads/main"
```

The condition deliberately uses numeric repository and owner IDs so a rename cannot silently transfer trust to another repository name.

A representative provider command is:

```bash
gcloud iam workload-identity-pools providers create-oidc panganlens-repo \
  --location="global" \
  --workload-identity-pool="panganlens-github" \
  --issuer-uri="https://token.actions.githubusercontent.com/" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref" \
  --attribute-condition='attribute.repository_id == "1335081180" && attribute.repository_owner_id == "179431732" && attribute.ref == "refs/heads/main"'
```

Use the current Google Cloud documentation when creating the pool and provider because IAM command details can evolve.

## Service account impersonation

The GitHub principal needs permission to impersonate only the dedicated PanganLens service account. Grant `roles/iam.workloadIdentityUser` to the principal set that represents this repository identity. Keep resource permissions, such as BigQuery dataset access, on the dedicated service account.

Do not create or upload a service account key file.

## Required GitHub repository variables

Configure these repository variables, not secrets containing JSON credentials:

- `GCP_PROJECT_ID`: Google Cloud project ID that owns the PanganLens datasets
- `GCP_WIF_PROVIDER`: full provider resource name using the numeric Google Cloud project number
- `GCP_SERVICE_ACCOUNT`: dedicated PanganLens service account email

The provider resource has this shape:

```text
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/panganlens-github/providers/panganlens-repo
```

The workflow preflight fails before requesting an OIDC token when any required variable is missing.

## BigQuery permission boundary

Start from dataset-level access rather than project-wide BigQuery administration. The ingestion identity needs enough permission to run query jobs and read or write only the PanganLens datasets used by raw, staging, core, mart, and ops processing.

Before granting a role, compare the exact operations in the current pipeline against the current Google Cloud IAM documentation. If a narrower custom role is practical later, prefer it over expanding permissions.

## Verification sequence

1. Create the workload identity pool and GitHub provider.
2. Apply the repository ID, owner ID, and `main` branch condition.
3. Create the dedicated service account and configure Workload Identity User impersonation.
4. Grant only the BigQuery access required by PanganLens.
5. Add the three GitHub repository variables.
6. Manually run `PanganLens GCP auth smoke test` from `main`.
7. Confirm the workflow reaches the BigQuery `SELECT 1` check without any service account key.
8. Only then proceed to scheduled production ingestion.

If authentication fails, do not weaken the provider condition as a shortcut. Verify the provider resource name, mapped claims, repository variables, service account binding, and BigQuery permissions first.
