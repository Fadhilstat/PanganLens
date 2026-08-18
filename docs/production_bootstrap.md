# Production bootstrap guard

PanganLens tidak menyiapkan BigQuery dengan menjalankan seluruh folder `sql/` sekaligus. Folder tersebut berisi campuran definisi schema, quality checks, audit queries, promotion logic, dan mapping activation. Menjalankannya tanpa klasifikasi dapat mengubah data pada urutan yang salah.

## Bootstrap yang aman

`python -m panganlens.bootstrap_plan_cli` hanya menghasilkan rencana dry-run. Perintah ini tidak membuat BigQuery client, tidak meminta credential Google Cloud, dan tidak mengeksekusi SQL.

Rencana schema mengikuti dependency berikut:

1. Buat dataset.
2. Buat core 3NF.
3. Buat raw, staging, dan operational tables.
4. Buat source mapping registry.
5. Buat mapping review queue.
6. Buat curated semantic views untuk dashboard.
7. Buat public publish-state view.

Setiap file pada rencana memiliki SHA-256 dan ukuran byte. Perubahan file therefore terlihat sebagai perubahan manifest saat dry-run berikutnya.

## SQL yang tidak ikut bootstrap

Quality checks, map QA, promotion staging ke core, post-promotion assertions, duplicate audit, dan mapping activation diklasifikasikan sebagai operational SQL. File tersebut tidak masuk schema bootstrap.

Beberapa schema files juga memiliki query audit read-only setelah DDL. Karena itu fase ini belum menyediakan automatic SQL executor. Executor produksi hanya boleh ditambahkan setelah statement classification, WIF smoke test, dan production readiness sudah tervalidasi pada environment Google Cloud yang sebenarnya.

## Prinsip operasional

- Default selalu dry-run.
- Tidak ada credential di repository.
- Tidak ada schedule produksi yang diaktifkan oleh bootstrap plan.
- Tidak ada mapping otomatis atau fuzzy matching.
- Jika ada file SQL baru yang belum diklasifikasikan, bootstrap plan gagal dan meminta review manusia.
- Production ingestion tetap tidak boleh dijadwalkan sampai WIF, reviewed mappings, dan readiness gate semuanya hijau.
