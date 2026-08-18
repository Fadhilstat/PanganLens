# Production bootstrap guard

PanganLens tidak menyiapkan BigQuery dengan menjalankan seluruh folder `sql/` sekaligus. Folder tersebut berisi campuran definisi schema, pemeriksaan kualitas, query audit, logika promotion, dan aktivasi mapping. Menjalankannya tanpa klasifikasi dapat mengubah data pada urutan yang salah.

## Bootstrap yang aman

`python -m panganlens.bootstrap_plan_cli` hanya menghasilkan rencana dry-run. Perintah ini tidak membuat BigQuery client, tidak meminta credential Google Cloud, dan tidak mengeksekusi SQL.

Rencana schema mengikuti urutan dependency berikut:

1. Buat dataset.
2. Buat core 3NF.
3. Buat tabel raw, staging, dan operasional.
4. Buat source mapping registry.
5. Buat mapping review queue.
6. Buat curated semantic views untuk dashboard.
7. Buat public publish-state view.

Setiap file pada rencana memiliki SHA-256 dan ukuran byte. Dengan begitu, perubahan isi file dapat terlihat pada dry-run berikutnya dan bisa diperiksa sebelum deployment.

## SQL yang tidak ikut bootstrap

Pemeriksaan kualitas, map QA, promotion staging ke core, post-promotion assertions, duplicate audit, dan mapping activation diklasifikasikan sebagai operational SQL. File tersebut tidak masuk schema bootstrap.

Beberapa schema files juga memiliki query audit read-only setelah DDL. Karena itu fase ini belum menyediakan executor SQL otomatis. Executor produksi hanya boleh ditambahkan setelah statement classification, WIF smoke test, dan production readiness tervalidasi pada environment Google Cloud yang sebenarnya.

## Prinsip operasional

- Default selalu dry-run.
- Tidak ada credential di repository.
- Tidak ada schedule produksi yang diaktifkan oleh bootstrap plan.
- Tidak ada mapping otomatis atau fuzzy matching.
- Jika ada file SQL baru yang belum diklasifikasikan, bootstrap plan gagal dan meminta review manusia.
- Production ingestion tetap tidak boleh dijadwalkan sampai WIF, reviewed mappings, dan readiness gate semuanya hijau.
