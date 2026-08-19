# Bootstrap plan evidence

Sebelum schema PanganLens boleh diterapkan ke BigQuery, operator perlu bukti plan yang dapat direview dan ditelusuri kembali ke commit tertentu. Workflow `PanganLens bootstrap plan` membuat bukti tersebut tanpa menghubungi Google Cloud.

Workflow ini sengaja manual dan hanya memakai `workflow_dispatch`. Ia tidak memiliki schedule, tidak meminta OIDC, tidak membaca secret cloud, dan tidak menjalankan `--apply`. Hak GitHub yang dipakai hanya `contents: read`.

## Cara kerja

Workflow checkout commit yang dipilih, memasang package dari repository, lalu menjalankan:

```bash
python -m panganlens.bootstrap_executor_cli --repo-root .
```

Plan JSON kemudian diproses oleh builder provenance yang hanya menerima metadata run dari GitHub Actions context. Builder memvalidasi bahwa workflow path, branch, commit SHA, event, dan contract plan sesuai dengan jalur bootstrap plan yang direview.

Artifact `panganlens-bootstrap-plan-<commit-sha>` disimpan selama 7 hari dan berisi dua file:

- `panganlens_bootstrap_plan.json`, berisi klasifikasi statement dan `plan_sha256`;
- `panganlens_bootstrap_plan_provenance.json`, berisi `plan_sha256`, `plan_run_id`, workflow path, branch `main`, head SHA, dan event `workflow_dispatch`.

Provenance dibuat otomatis dari `github.run_id`, `github.workflow_ref`, `github.ref_name`, `github.sha`, dan `github.event_name`. Operator tidak perlu mengetik ulang metadata run untuk bootstrap plan.

GitHub mendokumentasikan bahwa workflow dengan trigger `workflow_dispatch` dapat dijalankan secara manual dari Actions, CLI, atau REST API. GitHub Actions contexts menyediakan metadata workflow run, dan workflow artifacts dapat menyimpan output run setelah job selesai. PanganLens memakai mekanisme tersebut hanya sebagai jalur review, bukan deployment.

## Review sebelum apply

Operator harus:

1. Menjalankan workflow dari `main` setelah commit yang akan dipakai sudah direview.
2. Memastikan run selesai sukses.
3. Mengunduh artifact `panganlens-bootstrap-plan-<commit-sha>`.
4. Membaca `panganlens_bootstrap_plan.json` dan memastikan tidak ada statement yang tidak dipahami.
5. Memastikan `panganlens_bootstrap_plan_provenance.json` menunjuk ke run, workflow, branch, dan commit yang sama dengan run yang direview.
6. Memindahkan field provenance tersebut ke bagian `bootstrap` pada activation evidence tanpa mengubah nilainya.
7. Saat nanti ada bootstrap write identity yang sudah direview, gunakan `plan_sha256` yang sama bersama `--expected-plan-sha256` dan `--apply`.

Jika schema berubah setelah plan dibuat, hash dan provenance baru harus dihasilkan dan direview lagi. Jangan memakai plan lama untuk commit yang berbeda.

## Batas keamanan

Workflow plan ini tidak:

- meminta `GCP_PROJECT_ID`;
- meminta WIF provider;
- memakai `google-github-actions/auth`;
- meminta `id-token: write`;
- menjalankan BigQuery query;
- menjalankan `--apply`;
- mengaktifkan ingestion atau dashboard schedule.

Builder provenance juga fail closed. Ia menolak workflow ref yang berbeda, branch selain `main`, event selain `workflow_dispatch`, commit SHA yang tidak valid, plan hash yang tidak valid, plan tanpa executable schema statements, atau plan yang tidak lagi membutuhkan explicit apply.

Contract test di repository memeriksa batas tersebut agar perubahan workflow di masa depan gagal review jika jalur plan-only mulai bercampur dengan jalur apply atau provenance tidak lagi berasal dari GitHub context yang direview.

Bukti plan tetap bukan bukti bahwa schema sudah tersedia di BigQuery. Setelah real apply dilakukan melalui write boundary yang terpisah, status struktur cloud masih harus dibuktikan oleh bootstrap schema verifier dengan hasil `SCHEMA_READY`.
