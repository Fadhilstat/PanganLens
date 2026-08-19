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

Setelah langkah cloud benar-benar dijalankan, catat hanya metadata aman dari workflow run. `workflow_path`, `head_branch`, `head_sha`, dan `event` harus berasal dari run yang benar, bukan diketik berdasarkan asumsi.

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
    "plan_run_id": 123456790,
    "plan_workflow_path": ".github/workflows/bootstrap_plan.yml",
    "plan_head_branch": "main",
    "plan_head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "plan_event": "workflow_dispatch",
    "schema_verification_run_id": 123456791,
    "schema_status": "SCHEMA_READY",
    "schema_verification_workflow_path": ".github/workflows/bootstrap_schema_verification.yml",
    "schema_verification_head_branch": "main",
    "schema_verification_head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "schema_verification_event": "workflow_dispatch"
  },
  "readiness": {
    "run_id": 123456792,
    "status": "READY",
    "latest_source_capture_age_hours": 12,
    "workflow_path": ".github/workflows/bigquery_readiness.yml",
    "head_branch": "main",
    "head_sha": "40_CHARACTER_LOWERCASE_COMMIT_SHA",
    "event": "workflow_dispatch"
  }
}
```

`plan_head_sha` dan `schema_verification_head_sha` harus sama. Dengan begitu, schema yang direview melalui plan-only workflow dan schema yang kemudian diverifikasi berasal dari snapshot repository yang sama.

Validasi gate lengkap:

```bash
python -m panganlens.activation_evidence_cli \
  path/to/activation-evidence.json \
  --require-complete
```

`--require-complete` hanya lolos jika provider WIF sudah diverifikasi, auth smoke sukses, bootstrap plan memiliki run provenance yang valid, bootstrap verifier memiliki `schema_verification_run_id` yang valid dan menghasilkan `SCHEMA_READY`, full readiness menghasilkan `READY`, source capture tidak melewati batas freshness default 72 jam, dan seluruh workflow evidence berasal dari workflow manual yang direview pada branch `main`.

## Evidence fragment dari workflow

Workflow cloud manual sekarang membuat fragment activation evidence langsung dari GitHub Actions context. Nilai run ID, workflow ref, branch, commit SHA, dan event tidak perlu diketik ulang oleh operator.

- `PanganLens GCP auth smoke test` mengunggah `auth-smoke-evidence.json` setelah smoke query berhasil.
- `PanganLens bootstrap schema verification` mengunggah hasil verifier bersama `bootstrap-schema-verification-evidence.json`.
- `PanganLens BigQuery readiness` mengunggah hasil readiness bersama `bigquery-readiness-evidence.json`.

Artifact diberi nama yang terikat ke `github.sha` dan disimpan selama 7 hari. Untuk schema verification dan readiness, builder evidence memakai `if: always()` agar hasil `BLOCKED` tetap dapat direview jika checker sudah menghasilkan JSON. Status `BLOCKED` tidak diubah menjadi sukses dan workflow tetap mempertahankan conclusion aslinya.

Fragment tersebut hanya berisi metadata dan status yang sudah diizinkan oleh activation manifest. Ia tidak memuat credential, token, service-account JSON, atau isi file autentikasi yang dibuat sementara oleh GitHub Actions.

## Provenance workflow

Run ID saja tidak cukup untuk completion evidence. Setiap bukti workflow lengkap harus membawa:

- exact workflow path yang direview;
- `head_branch` bernilai `main`;
- commit `head_sha` lowercase 40 karakter;
- event `workflow_dispatch`.

Kontrak ini berlaku untuk auth smoke, bootstrap plan, schema verification, dan readiness. Bootstrap plan harus membawa `plan_run_id`, bukan hanya `plan_sha256`. Schema verification juga harus membawa `schema_verification_run_id` agar status `SCHEMA_READY` dapat ditelusuri langsung ke workflow run yang menghasilkannya. Hash atau status yang diketik manual tanpa run provenance tidak cukup untuk menutup gate Phase 2.

Kontrak ini mencegah run sukses dari workflow lain, branch eksperimen, trigger yang tidak direview, atau plan dari commit berbeda ikut dipakai sebagai bukti Phase 2. Validator tetap tidak mencoba menghubungi GitHub. Operator tetap harus memastikan artifact berasal dari workflow run yang direview sebelum memasukkan fragment ke manifest utama.

## Yang boleh dicatat

- GitHub workflow run ID.
- Workflow path, head branch, head commit SHA, dan event dari run yang direview.
- Google Cloud project ID.
- Full WIF provider resource name yang sudah direview.
- Boolean bahwa effective provider condition telah diperiksa.
- Exact reviewed `plan_sha256` dari artifact bootstrap plan yang sesuai.
- Status `SCHEMA_READY`, `BLOCKED`, `READY`, atau conclusion workflow yang didukung.
- Umur source capture dalam jam untuk membuktikan freshness gate.

## Yang tidak boleh dicatat

Jangan menaruh access token, ID token, refresh token, password, secret, service-account JSON, private key, credential file, atau credential-like payload di manifest. Validator menolak nama field sensitif secara rekursif dan juga menolak marker private key atau service-account JSON yang muncul di nilai string.

Jika sebuah bukti hanya tersedia sebagai log mentah, simpan run ID dan metadata provenance yang aman lalu review log di sistem asal. Jangan menyalin seluruh log ke repository atau GitHub Issue #48.

## Hubungan dengan Issue #48

Manifest adalah indeks bukti, bukan sumber kebenaran cloud. Status tetap berasal dari workflow dan verifier masing-masing:

1. WIF provider diperiksa dari effective Google Cloud configuration.
2. Auth smoke berasal dari `PanganLens GCP auth smoke test` pada `main` dan fragment evidence dibuat setelah query berhasil.
3. Bootstrap plan hash berasal dari artifact `PanganLens bootstrap plan` pada `main`, lengkap dengan run provenance.
4. Plan dan schema verification harus memakai head commit yang sama.
5. `SCHEMA_READY` berasal dari metadata-only bootstrap verifier pada `main` dan harus membawa run ID verifier yang valid.
6. `READY` dan source freshness berasal dari BigQuery readiness inspector pada `main`.
7. Workflow provenance berasal dari metadata GitHub Actions run yang sesuai dan dibundel otomatis pada artifact workflow yang mendukungnya.

Production ingestion dan recurring dashboard refresh tetap tidak boleh diaktifkan hanya karena manifest valid. Semua gate Issue #48 tetap berlaku, termasuk IAM minimum privilege, mapping review, duplicate and conflict controls, data quality, publish state, mart checks, source health, dan cost boundary.
