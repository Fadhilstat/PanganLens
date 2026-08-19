# Cloud activation evidence

Phase 2 membutuhkan bukti operasional yang nyata, tetapi repository tidak boleh menjadi tempat penyimpanan credential, token, service-account JSON, atau material IAM sensitif. Karena itu PanganLens memakai manifest kecil yang hanya berisi identifier dan status yang aman untuk direview.

Validator ini tidak menghubungi Google Cloud dan tidak menggantikan workflow atau verifier yang sebenarnya. Fungsinya adalah memastikan bukti yang dicatat memiliki bentuk yang konsisten, tidak memuat field sensitif, dan tidak menyatakan Phase 2 selesai jika gate penting masih `BLOCKED`.

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

Setelah langkah cloud benar-benar dijalankan, manifest dapat mencatat hanya hasil yang aman:

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
    "conclusion": "success"
  },
  "bootstrap": {
    "plan_sha256": "REVIEWED_64_CHARACTER_LOWERCASE_SHA256",
    "schema_verification_run_id": 123456790,
    "schema_status": "SCHEMA_READY"
  },
  "readiness": {
    "run_id": 123456791,
    "status": "READY",
    "latest_source_capture_age_hours": 12
  }
}
```

Validasi gate lengkap:

```bash
python -m panganlens.activation_evidence_cli \
  path/to/activation-evidence.json \
  --require-complete
```

`--require-complete` hanya lolos jika provider WIF sudah diverifikasi, auth smoke sukses, bootstrap verifier menghasilkan `SCHEMA_READY`, full readiness menghasilkan `READY`, dan source capture yang dicatat tidak melewati batas freshness default 72 jam.

## Yang boleh dicatat

- GitHub workflow run ID.
- Google Cloud project ID.
- Full WIF provider resource name yang sudah direview.
- Boolean bahwa effective provider condition telah diperiksa.
- Exact reviewed `plan_sha256`.
- Status `SCHEMA_READY`, `BLOCKED`, `READY`, atau conclusion workflow yang didukung.
- Umur source capture dalam jam untuk membuktikan freshness gate.

## Yang tidak boleh dicatat

Jangan menaruh access token, ID token, refresh token, password, secret, service-account JSON, private key, credential file, atau credential-like payload di manifest. Validator menolak nama field sensitif secara rekursif dan juga menolak marker private key atau service-account JSON yang muncul di nilai string.

Jika sebuah bukti hanya tersedia sebagai log mentah, simpan link atau run ID yang aman dan review log di sistem asal. Jangan menyalin seluruh log ke repository atau GitHub Issue #48.

## Hubungan dengan Issue #48

Manifest adalah indeks bukti, bukan sumber kebenaran cloud. Status tetap berasal dari workflow dan verifier masing-masing:

1. WIF provider diperiksa dari effective Google Cloud configuration.
2. Auth smoke berasal dari `PanganLens GCP auth smoke test`.
3. Bootstrap plan hash berasal dari executor plan-only yang direview sebelum apply.
4. `SCHEMA_READY` berasal dari metadata-only bootstrap verifier.
5. `READY` dan source freshness berasal dari BigQuery readiness inspector.

Production ingestion dan recurring dashboard refresh tetap tidak boleh diaktifkan hanya karena manifest valid. Semua gate Issue #48 tetap berlaku, termasuk IAM minimum privilege, mapping review, duplicate and conflict controls, data quality, publish state, mart checks, source health, dan cost boundary.
