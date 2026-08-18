# Direct keyless Google Cloud authentication for PanganLens

PanganLens uses GitHub Actions OpenID Connect with Google Cloud Workload Identity Federation. The read-only cloud workflows authenticate directly as the federated GitHub principal. They do not use a service account and do not require a long-lived JSON key.

This setup remains separate from production ingestion. First verify direct WIF and read-only BigQuery access through the manual smoke test and readiness workflows. Production write access must be designed and approved separately rather than expanding this read-only identity.

## Fixed GitHub identity

Use immutable GitHub identifiers in the provider condition:

- repository: `Fadhilstat/PanganLens`
- repository ID: `1335081180`
- repository owner: `Fadhilstat`
- repository owner ID: `179431732`
- production branch: `refs/heads/main`

GitHub includes numeric repository and owner IDs in its Actions OIDC token. Google Cloud recommends numeric `*_id` claims instead of repository or owner names because the numeric IDs are unique and cannot be reused after a rename or deletion.

## Recommended Google Cloud objects

Use a dedicated pool and provider for PanganLens:

- workload identity pool: `panganlens-github`
- provider: `panganlens-repo`

The current read-only workflows do not need a Google Cloud service account. Direct WIF keeps the trust relationship smaller and removes service-account impersonation from this path.

## Step 1: select the Google Cloud project

Set the project that owns the PanganLens BigQuery datasets:

```bash
export GCP_PROJECT_ID="YOUR_PROJECT_ID"
gcloud config set project "$GCP_PROJECT_ID"
export GCP_PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
```

The provider resource name and principal-set IAM member must use the numeric Google Cloud project number.

## Step 2: create the workload identity pool

```bash
gcloud iam workload-identity-pools create panganlens-github \
  --project="$GCP_PROJECT_ID" \
  --location="global" \
  --display-name="PanganLens GitHub Actions"
```

If the pool already exists, inspect it instead of creating a second pool.

## Step 3: create the GitHub OIDC provider

Map only the claims used by PanganLens trust rules:

```text
google.subject=assertion.sub
attribute.repository_id=assertion.repository_id
attribute.repository_owner_id=assertion.repository_owner_id
attribute.ref=assertion.ref
```

Create the provider with the official GitHub Actions issuer and a condition that accepts only this repository, this owner, and `main`:

```bash
gcloud iam workload-identity-pools providers create-oidc panganlens-repo \
  --project="$GCP_PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="panganlens-github" \
  --display-name="PanganLens repository" \
  --issuer-uri="https://token.actions.githubusercontent.com/" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref" \
  --attribute-condition='attribute.repository_id == "1335081180" && attribute.repository_owner_id == "179431732" && attribute.ref == "refs/heads/main"'
```

Do not weaken the condition to repository names only if authentication fails. Check the mapped claims, provider resource name, selected branch, and IAM bindings first.

## Step 4: derive the direct WIF principal

```bash
export WIF_POOL_RESOURCE="projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/panganlens-github"
export PANGANLENS_GITHUB_PRINCIPAL="principalSet://iam.googleapis.com/${WIF_POOL_RESOURCE}/attribute.repository_id/1335081180"
```

The provider already restricts the owner ID and `main` branch. The principal-set binding further limits resource access to the immutable PanganLens repository ID.

## Step 5: grant only query-job permission at project level

The read-only workflows need permission to create BigQuery query jobs:

```bash
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="$PANGANLENS_GITHUB_PRINCIPAL" \
  --role="roles/bigquery.jobUser"
```

Do not grant Owner, Editor, BigQuery Admin, or BigQuery User merely for convenience. `roles/bigquery.jobUser` is intentionally narrower for this path.

## Step 6: grant dataset-level read access

Grant `roles/bigquery.dataViewer` to the same principal only on PanganLens datasets required by the manual read-only workflows:

- `panganlens_raw`
- `panganlens_staging`
- `panganlens_core`
- `panganlens_mart`
- `panganlens_ops`

The readiness inspector reads metadata across all five datasets and queries `ops` and `mart`. The website snapshot exporter reads only `panganlens_mart`, but using the same read-only principal keeps the manual verification path simple.

Prefer dataset-level access through BigQuery IAM instead of granting Data Viewer across a shared Google Cloud project. If the Google Cloud project is dedicated only to PanganLens, project-level Data Viewer is simpler but broader and should still be an explicit choice.

## Step 7: store only two GitHub repository variables

Configure these repository variables:

- `GCP_PROJECT_ID`: Google Cloud project ID that owns the PanganLens datasets
- `GCP_WIF_PROVIDER`: full provider resource name

The provider resource has this shape:

```text
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/panganlens-github/providers/panganlens-repo
```

`GCP_SERVICE_ACCOUNT` is not used by the direct WIF workflows and should not be required for this read-only path.

Do not create or upload a service account key file. Do not add `credentials_json` to GitHub secrets.

## Step 8: verify in a strict order

1. Run `PanganLens GCP auth smoke test` manually from `main`.
2. Confirm the workflow reaches the BigQuery `SELECT 1` query using direct WIF.
3. Run `PanganLens BigQuery readiness` manually from `main`.
4. Read the `READY` or `BLOCKED` JSON evidence. A `BLOCKED` result is expected until schema, mappings, source evidence, publish state, and marts are complete.
5. Only after the read-only path is proven should production bootstrap execution or ingestion write permissions be considered.

## Production write access stays separate

The current direct WIF principal is deliberately read-only. Production ingestion will eventually need controlled writes to raw, staging, core, ops, and mart-related resources. Do not solve that by adding broad write roles to the read-only principal.

When production ingestion reaches that phase, create a separately reviewed write boundary with the minimum dataset roles required by the actual code path. Keep the source probe, readiness, and website snapshot workflows read-only.

## Cost boundary

The smoke query and readiness queries are small and bounded by the code where applicable, but BigQuery remains a metered service. Keep billing alerts and query controls enabled. If portfolio usage approaches the free-tier allowance, reduce or stop refreshes instead of silently accepting charges.

## Verified references

These primary sources were checked live on 18 August 2026 before this onboarding was updated:

- Google Cloud, Workload Identity Federation with deployment pipelines: https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- Google Cloud SDK, `gcloud iam workload-identity-pools providers create-oidc`: https://cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/providers/create-oidc
- Google Cloud, BigQuery IAM roles and permissions: https://cloud.google.com/bigquery/docs/access-control
- `google-github-actions/auth`, direct Workload Identity Federation setup: https://github.com/google-github-actions/auth#direct-wif
