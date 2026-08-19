# Cloud activation evidence

Phase 2 membutuhkan bukti operasional yang nyata, tetapi repository tidak boleh menjadi tempat penyimpanan credential, token, service-account JSON, atau material IAM sensitif. Karena itu PanganLens memakai manifest kecil yang hanya berisi identifier, provenance workflow, dan status yang aman untuk direview.

Validator ini tidak menghubungi Google Cloud dan tidak menggantikan workflow atau verifier yang sebenarnya. Fungsinya adalah memastikan bukti yang dicatat memiliki bentuk yang konsisten, tidak memuat field sensitif, dan tidak menyatakan Phase 2 selesai jika gate penting masih `BLOCKED` atau berasal dari workflow yang salah.

## Bentuk minimum

Manifest dapat dibuat bertahap. Jangan mengisi status masa depan dengan nilai buatan hanya agar file terlihat lengkap.

```json
{
  "repository": {
    "full_name": "Fadhilstat/PanganLens",
    "repository_id": 1335081180,
    "owner_id": 179431732
  },
  "gcp": {
    "project_id": "YOUR_GCP_PROJECT_ID",
    "wif_provider": "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/panganlens-github/providers/panganlens-repo"
  }
}
```

Validasi manifest parsial:

```bash
python -m panganlens.activation_evidence_cli path/to/activation-evidence.json
```

## Bukti lengkap untuk gate Phase 2

Setelah langkah cloud benar-benar dijalankan, catat hanya metadata aman dari workflow run. `workflow_path`, `head_branch`, `head_sha`, dan `event` harus diambil dari run yang benar, bukan diketik berdasarkan asumsi.

```json
{
  "repository": {
    "full_name": "Fadhilstat/PanganLens",
    "repository_id": 1335081180,
    "owner_id": 179431732
  },
  "gcp": {
    "project_id": "YOUR_GCP_PROJECT_ID",
    "wif_provider": "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/panganlens-github/providers/panganlens-repo"
  },
  "wif": {
    "provider_verified": true
  },
  "auth_smoke": {
    "run_id": 123456789,
    "conclusion": "success",
    "workflow_path": ".github/workflows/gcp_auth_smoke.yml",
    "head_branch": "main",
    "head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "event": "workflow_dispatch"
  },
  "bootstrap": {
    "plan_sha256": "REVIEWED_64_CHARACTER_LOWERCASE_SHA256",
    "schema_verification_run_id": 123456790,
    "schema_status": "SCHEMA_READY",
    "schema_verification_workflow_path": ".github/workflows/bootstrap_schema_verification.yml",
    "schema_verification_head_branch": "main",
    "schema_verification_head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "schema_verification_event": "workflow_dispatch"
  },
  "readiness": {
    "run_id": 123456791,
    "status": "READY",
    "latest_source_capture_age_hours": 12,
    "workflow_path": ".github/workflows/bigquery_readiness.yml",
    "head_branch": "main",
    "head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "event": "workflow_dispatch"
  }
}
```

Validasi gate lengkap:

```bash
python -m panganlens.activation_evidence_cli \
  path/to/activation-evidence.json \
  --require-complete
```

`--require-complete` hanya lolos jika provider WIF sudah diverifikasi, auth smoke sukses, bootstrap verifier menghasilkan `SCHEMA_READY`, full readiness menghasilkan `READY`, source capture tidak melewati batas freshness default 72 jam, dan ketiga workflow evidence memiliki provenance yang sesuai dengan workflow manual yang direview pada branch `main`.

## Provenance workflow

Run ID saja tidak cukup untuk completion evidence. Setiap bukti workflow lengkap harus membawa:

- exact workflow path yang direview;
- `head_branch` bernilai `main`;
- commit `head_sha` lowercase 40 karakter;
- event `workflow_dispatch`.

Kontrak ini mencegah run sukses dari workflow lain, branch eksperimen, atau trigger yang tidak direview ikut dipakai sebagai bukti Phase 2. Validator tetap tidak mencoba menghubungi GitHub. Operator harus membandingkan nilai manifest dengan metadata workflow run di GitHub sebelum menyimpannya.

## Yang boleh dicatat

- GitHub workflow run ID.
- Workflow path, head branch, head commit SHA, dan event dari run yang direview.
- Google Cloud project ID.
- Full WIF provider resource name yang sudah direview.
- Boolean bahwa effective provider condition telah diperiksa.
- Exact reviewed `plan_sha256`.
- Status `SCHEMA_READY`, `BLOCKED`, `READY`, atau conclusion workflow yang didukung.
- Umur source capture dalam jam untuk membuktikan freshness gate.

## Yang tidak boleh dicatat

Jangan menaruh access token, ID token, refresh token, password, secret, service-account JSON, private key, credential file, atau credential-like payload di manifest. Validator menolak nama field sensitif secara rekursif dan juga menolak marker private key atau service-account JSON yang muncul di nilai string.

Jika sebuah bukti hanya tersedia sebagai log mentah, simpan run ID dan metadata provenance yang aman lalu review log di sistem asal. Jangan menyalin seluruh log ke repository atau GitHub Issue #48.

## Hubungan dengan Issue #48

Manifest adalah indeks bukti, bukan sumber kebenaran cloud. Status tetap berasal dari workflow dan verifier masing-masing:

1. WIF provider diperiksa dari effective Google Cloud configuration.
2. Auth smoke berasal dari `PanganLens GCP auth smoke test` pada `main`.
3. Bootstrap plan hash berasal dari executor plan-only yang direview sebelum apply.
4. `SCHEMA_READY` berasal dari metadata-only bootstrap verifier pada `main`.
5. `READY` dan source freshness berasal dari BigQuery readiness inspector pada `main`.
6. Workflow provenance berasal dari metadata GitHub Actions run yang sesuai.

Production ingestion dan recurring dashboard refresh tetap tidak boleh diaktifkan hanya karena manifest valid. Semua gate Issue #48 tetap berlaku, termasuk IAM minimum privilege, mapping review, duplicate and conflict controls, data quality, publish state, mart checks, source health, dan cost boundary.
