# Bootstrap plan evidence

Sebelum schema PanganLens boleh diterapkan ke BigQuery, operator perlu bukti plan yang dapat direview dan ditelusuri kembali ke commit tertentu. Workflow `PanganLens bootstrap plan` membuat bukti tersebut tanpa menghubungi Google Cloud.

Workflow ini sengaja manual dan hanya memakai `workflow_dispatch`. Ia tidak memiliki schedule, tidak meminta OIDC, tidak membaca secret cloud, dan tidak menjalankan `--apply`. Hak GitHub yang dipakai hanya `contents: read`.

## Cara kerja

Workflow checkout commit yang dipilih, memasang package dari repository, lalu menjalankan:

```bash
python -m panganlens.bootstrap_executor_cli --repo-root .
```

Output JSON disimpan sebagai artifact bernama `panganlens-bootstrap-plan-<commit-sha>` selama 7 hari. JSON tersebut memuat klasifikasi statement dan `plan_sha256` yang berasal dari isi schema pada commit itu.

GitHub mendokumentasikan bahwa workflow dengan trigger `workflow_dispatch` dapat dijalankan secara manual dari Actions, CLI, atau REST API. GitHub juga menyediakan workflow artifacts untuk menyimpan output run setelah job selesai. PanganLens memakai dua mekanisme itu hanya sebagai jalur review, bukan deployment.

## Review sebelum apply

Operator harus:

1. Menjalankan workflow dari `main` setelah commit yang akan dipakai sudah direview.
2. Memastikan run selesai sukses.
3. Mengunduh artifact `panganlens-bootstrap-plan-<commit-sha>`.
4. Membaca isi plan dan memastikan tidak ada statement yang tidak dipahami.
5. Mencatat exact `plan_sha256` di activation evidence hanya setelah review manusia selesai.
6. Saat nanti ada bootstrap write identity yang sudah direview, gunakan hash yang sama bersama `--expected-plan-sha256` dan `--apply`.

Jika schema berubah setelah plan dibuat, hash baru harus dihasilkan dan direview lagi. Jangan memakai plan lama untuk commit yang berbeda.

## Batas keamanan

Workflow plan ini tidak:

- meminta `GCP_PROJECT_ID`;
- meminta WIF provider;
- memakai `google-github-actions/auth`;
- meminta `id-token: write`;
- menjalankan BigQuery query;
- menjalankan `--apply`;
- mengaktifkan ingestion atau dashboard schedule.

Contract test di repository memeriksa batas tersebut agar perubahan workflow di masa depan gagal review jika jalur plan-only mulai bercampur dengan jalur apply.

Bukti plan tetap bukan bukti bahwa schema sudah tersedia di BigQuery. Setelah real apply dilakukan melalui write boundary yang terpisah, status struktur cloud masih harus dibuktikan oleh bootstrap schema verifier dengan hasil `SCHEMA_READY`.
