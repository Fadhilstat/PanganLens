# Production bootstrap guard

PanganLens tidak menyiapkan BigQuery dengan menjalankan seluruh folder `sql/` sekaligus. Folder tersebut berisi campuran definisi schema, pemeriksaan kualitas, query audit, logika promotion, dan aktivasi mapping. Menjalankannya tanpa klasifikasi dapat mengubah data pada urutan yang salah.

## Bootstrap yang aman

`python -m panganlens.bootstrap_plan_cli` tetap menjadi rencana file-level yang tidak membuat BigQuery client dan tidak mengeksekusi SQL.

Untuk pemeriksaan yang lebih detail, jalankan:

```bash
python -m panganlens.bootstrap_executor_cli --repo-root .
```

Perintah tersebut masih plan-only. Ia memecah setiap schema file menjadi statement, mengklasifikasikan tiap statement, lalu mencetak `plan_sha256`. Tidak diperlukan project ID atau credential Google Cloud pada mode ini.

Rencana schema mengikuti urutan dependency berikut:

1. Buat dataset.
2. Buat core 3NF.
3. Buat tabel raw, staging, dan operasional.
4. Buat source mapping registry.
5. Buat mapping review queue.
6. Buat curated semantic views untuk dashboard.
7. Buat public publish-state view.

Setiap file dan statement memiliki SHA-256. Perubahan isi SQL akan mengubah `plan_sha256`, sehingga rencana lama tidak bisa dipakai untuk mengeksekusi SQL yang sudah berubah.

## Statement yang boleh dieksekusi

Executor hanya mengizinkan bentuk schema yang saat ini memang dibutuhkan PanganLens:

- `CREATE SCHEMA IF NOT EXISTS panganlens_*`
- `CREATE TABLE IF NOT EXISTS panganlens_*.*`
- `CREATE OR REPLACE VIEW panganlens_*.* AS ...`

Dataset dibatasi ke `panganlens_raw`, `panganlens_staging`, `panganlens_core`, `panganlens_mart`, dan `panganlens_ops`.

`SELECT` standalone di schema files diperlakukan sebagai audit read-only dan dicatat sebagai `SKIP_AUDIT`. Statement tersebut tidak dieksekusi oleh bootstrap executor.

`DROP`, `DELETE`, `UPDATE`, `INSERT`, `MERGE`, `CREATE OR REPLACE TABLE`, `CREATE TABLE AS SELECT`, serta bentuk lain yang belum direview membuat plan gagal. Prinsipnya sederhana: statement baru harus diklasifikasikan dengan sengaja sebelum bisa menyentuh BigQuery.

## Apply yang eksplisit

Eksekusi nyata tidak pernah menjadi default. Operator harus lebih dulu menghasilkan dan mereview plan, lalu memasukkan hash yang sama secara eksplisit:

```bash
python -m panganlens.bootstrap_executor_cli \
  --repo-root . \
  --project-id YOUR_GCP_PROJECT_ID \
  --expected-plan-sha256 REVIEWED_PLAN_SHA256 \
  --apply
```

Sebelum query pertama dijalankan, executor membangun ulang plan dari file saat itu. Jika hash berbeda, seluruh apply berhenti tanpa mengeksekusi SQL. Executor juga memverifikasi project ID dan, jika client diberikan dari kode, memastikan project client sama dengan target project.

Eksekusi berhenti pada statement pertama yang gagal. Audit `SELECT` tetap dilewati. Tidak ada operational SQL, ingestion, promotion, mapping activation, atau publish pointer update di jalur bootstrap ini.

## Verifikasi schema setelah apply

Sesudah real apply dilakukan pada environment Google Cloud milik operator, schema dapat diperiksa tanpa membaca isi tabel:

```bash
python -m panganlens.bootstrap_verifier_cli \
  --project-id YOUR_GCP_PROJECT_ID
```

Verifier hanya memakai metadata dataset dan object. Ia memastikan:

- lima dataset PanganLens tersedia;
- lokasi dataset sesuai `asia-southeast2`;
- seluruh tabel dan view hasil bootstrap tersedia;
- setiap object mempunyai tipe yang benar, sehingga logical view tidak diam-diam terganti menjadi table atau sebaliknya;
- intermediate view `vw_looker_latest_region_price` ikut diperiksa karena menjadi dependency province map.

Jika semua metadata sesuai, statusnya `SCHEMA_READY`. Status ini sengaja berbeda dari full production `READY`. `SCHEMA_READY` hanya berarti struktur BigQuery hasil bootstrap sudah lengkap dan berada di lokasi yang benar. Ia belum membuktikan bahwa mapping, source capture, data quality, cost guards, publish state, atau mart data sudah siap.

Verifier tidak menjalankan query terhadap row data. Jika dataset atau object hilang, lokasi berbeda, tipe object salah, atau metadata tidak dapat dibaca, status menjadi `BLOCKED`.

## SQL yang tidak ikut bootstrap

Pemeriksaan kualitas, map QA, promotion staging ke core, post-promotion assertions, duplicate audit, dan mapping activation atau rejection diklasifikasikan sebagai operational SQL. File tersebut tidak masuk schema bootstrap.

Contohnya, `008_source_mapping_registry.sql` dan `015_mapping_review_queue.sql` memiliki DDL diikuti query audit. Statement-level classification membuat DDL tetap dapat dipersiapkan untuk bootstrap tanpa ikut menjalankan query audit tersebut.

## Status produksi saat ini

Adanya executor dan verifier bukan berarti production bootstrap sudah dijalankan. Real apply tetap harus menunggu konfigurasi Google Cloud milik operator, direct WIF smoke test, dan pengecekan IAM yang benar. Repository tidak menyimpan credential dan tidak menambahkan hak write ke principal read-only yang sudah dirancang untuk readiness.

Workflow produksi juga tetap tidak dijadwalkan. Setelah real bootstrap tersedia, mapping dan readiness masih harus lolos sebelum ingestion atau dashboard snapshot refresh boleh diaktifkan secara terjadwal.

## Prinsip operasional

- Default selalu plan-only.
- Apply membutuhkan flag `--apply` dan exact reviewed `plan_sha256`.
- Verifikasi schema bersifat metadata-only dan terpisah dari full production readiness.
- Tidak ada credential di repository.
- Tidak ada schedule produksi yang diaktifkan oleh bootstrap executor.
- Tidak ada mapping otomatis atau fuzzy matching.
- Jika ada file SQL atau statement baru yang belum diklasifikasikan, bootstrap gagal dan meminta review manusia.
- Production ingestion tetap tidak boleh dijadwalkan sampai WIF, reviewed mappings, cost guards, data-quality checks, dan readiness semuanya hijau.

## Referensi resmi yang diverifikasi

Dokumentasi Google Cloud untuk BigQuery DDL, metadata tabel/view, dan Python client diverifikasi masih dapat diakses pada 18 Agustus 2026. Executor mengikuti bentuk DDL BigQuery yang terdokumentasi. Verifier menggunakan metadata object dan tidak membutuhkan query terhadap isi tabel untuk membedakan struktur table dan view.