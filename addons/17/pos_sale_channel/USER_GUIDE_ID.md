# Panduan Pengguna POS Sale Channel dan Online Order Checker

Dokumen ini menjelaskan penggunaan modul `pos_sale_channel` pada Odoo 17, termasuk pengaturan sales channel di POS dan flow `Online Order Checker` untuk order online seperti `GrabFood`, `GoFood`, `ShopeeFood`, `Tokopedia`, atau channel online lain yang dipilih pada konfigurasi POS.

Panduan ini ditujukan untuk:

1. Admin atau supervisor POS yang melakukan konfigurasi.
2. Kasir atau operator outlet yang membuat order online di POS.
3. Supervisor atau manager yang perlu melakukan override atau reopen checker.

## 1. Tujuan Modul

Modul ini memiliki 2 fungsi utama:

1. Menandai transaksi POS berdasarkan `Sales Channel`.
2. Menambahkan flow `Online Order Checker` untuk memastikan item fisik yang disiapkan untuk pickup sesuai dengan order online.

Dengan flow checker ini, outlet memiliki proses kontrol antara:

1. Item yang dipesan customer melalui channel online.
2. Item yang sudah benar-benar disiapkan untuk diambil driver.

## 2. Ringkasan Hasil yang Diharapkan

Jika modul sudah dikonfigurasi dengan benar, hasil yang diharapkan adalah:

1. Kasir bisa memilih `Sales Channel` pada order POS.
2. Outlet bisa menentukan channel mana saja yang dianggap `online` dan wajib checker.
3. Setelah order online dibayar, status checker otomatis menjadi `Pending`.
4. User bisa membuka checker dari `Receipt Screen` atau dari `Ticket Screen`.
5. User bisa mencatat progres pengecekan per item dan per quantity.
6. Order dianggap selesai dicek jika semua quantity match, atau jika manager melakukan override dengan alasan.
7. Checker yang sudah selesai tidak bisa diubah lagi oleh user biasa.
8. Hanya `POS Manager` yang bisa melakukan `override` atau `reopen`.

## 3. Konfigurasi Awal

### 3.1. Menyiapkan Sales Channel

Langkah:

1. Buka menu `Point of Sale > Configuration > Sales Channels`.
2. Pastikan channel yang dibutuhkan sudah tersedia, misalnya:
   - `Dine In`
   - `Takeaway`
   - `GrabFood`
   - `GoFood`
   - `ShopeeFood`
   - `Tokopedia`
   - `Shopee`
3. Jika perlu, buat channel tambahan sesuai operasional outlet.
4. Atur `Sequence` agar urutan channel sesuai kebutuhan.
5. Simpan.

Expected outcome:

1. Channel tampil di POS dan bisa dipilih pada order.
2. Channel bisa dipakai juga untuk reporting dan filter order di backend.

### 3.2. Menentukan Channel yang Wajib Online Checker

Langkah:

1. Buka menu `Point of Sale > Configuration > Point of Sale`.
2. Buka POS config yang digunakan outlet.
3. Cari blok `Online Order Checker`.
4. Isi field `Online Checker Channels` dengan channel yang wajib checker, misalnya:
   - `GrabFood`
   - `GoFood`
   - `ShopeeFood`
   - `Tokopedia`
   - `Shopee`
5. Simpan.

Expected outcome:

1. Hanya order dengan channel yang dipilih di field ini yang akan masuk flow checker.
2. Channel lain seperti `Dine In` atau `Takeaway` tidak akan memicu checker kecuali ikut dipilih.

Catatan:

1. Modul tidak menggunakan hardcode nama channel.
2. Penentuan channel online sepenuhnya mengikuti konfigurasi POS.

## 4. Penggunaan Sales Channel di POS

### 4.1. Mengatur Channel untuk Order

Langkah:

1. Buka sesi POS.
2. Buat order seperti biasa.
3. Gunakan tombol `Order Channel`.
4. Pilih channel order yang sesuai.

Expected outcome:

1. Order tersimpan dengan `Sales Channel` yang dipilih.
2. Semua line default mengikuti channel order.

### 4.2. Mengatur Channel untuk Item Tertentu

Langkah:

1. Pilih line item pada order.
2. Gunakan tombol `Item Channel`.
3. Pilih:
   - `Follow Order Channel`, atau
   - channel tertentu untuk item tersebut.

Expected outcome:

1. Line item bisa memakai channel yang berbeda dari order jika dibutuhkan.
2. Flow checker hanya menghitung line yang effective channel-nya termasuk channel online checker.

## 5. Flow Online Order Checker

## 5.1. Kapan Checker Digunakan

Checker berlaku pada order yang:

1. Sudah dibayar.
2. Menggunakan `Sales Channel` yang termasuk `Online Checker Channels`.

Setelah payment berhasil:

1. Order online otomatis ditandai `Pending`.
2. User bisa langsung mulai checker dari `Receipt Screen`.
3. Jika checker belum dilakukan, order tetap bisa dibuka lagi dari `Ticket Screen`.

## 5.2. Status Checker

Status yang digunakan pada order:

1. `Not Required`
   Digunakan untuk order yang tidak termasuk flow checker.
2. `Pending`
   Order wajib checker, tetapi belum ada quantity yang dicek.
3. `In Progress`
   User sudah mulai mengisi checked quantity.
4. `Checked`
   Semua quantity line checker sudah match penuh.
5. `Overridden`
   Checker diselesaikan paksa oleh manager dengan alasan.

## 5.3. Membuka Checker dari Receipt Screen

Langkah:

1. Selesaikan payment order online.
2. Pada `Receipt Screen`, klik tombol `Start Checker` atau `Open Checker`.

Expected outcome:

1. Sistem membuka layar `Online Order Checker`.
2. Order dan line checker dimuat dari data server.

## 5.4. Membuka Checker dari Ticket Screen

Langkah:

1. Masuk ke `Ticket Screen`.
2. Pilih order online yang ingin dicek atau dicek ulang.
3. Klik tombol `Start Checker` atau `Open Checker`.

Expected outcome:

1. Checker bisa dibuka lagi untuk order yang sama.
2. Progress sebelumnya tetap tersimpan.

## 5.5. Mengecek Item per Quantity

Pada layar checker, setiap line menampilkan:

1. Nama item.
2. Ordered quantity.
3. Checked quantity.
4. Remaining quantity.
5. Status line:
   - `unchecked`
   - `partial`
   - `full`

Action yang tersedia:

1. `+1`
   Menambah checked quantity sebanyak 1.
2. `Set Full`
   Mengisi checked quantity sama dengan ordered quantity.
3. `Reset`
   Mengembalikan checked quantity line menjadi 0.

Expected outcome:

1. User bisa melakukan pengecekan parsial.
2. Progress quantity dan progress line langsung ter-update di layar.

## 5.6. Menyimpan Progress

Langkah:

1. Isi checked quantity sesuai item yang sudah selesai disiapkan.
2. Isi `Pickup / Driver Note` jika diperlukan.
3. Klik `Save Progress`.

Expected outcome:

1. Progress tersimpan di backend.
2. Status order menjadi `In Progress` jika sebelumnya masih `Pending`.
3. User bisa melanjutkan checker nanti tanpa kehilangan progress.

Contoh penggunaan:

1. Order memiliki 3 line, tetapi baru 2 line yang siap.
2. User bisa menyimpan progress parsial tanpa harus menunggu semua item selesai.

## 5.7. Menyelesaikan Checker dengan Match Penuh

Langkah:

1. Pastikan semua checked quantity sudah sama dengan ordered quantity.
2. Klik `Complete Checker`.

Expected outcome:

1. Status order berubah menjadi `Checked`.
2. Checker terkunci dari perubahan lebih lanjut oleh user biasa.
3. Sistem menyimpan user dan waktu penyelesaian checker.

Catatan:

1. Tombol `Complete Checker` hanya bisa dipakai jika semua quantity sudah match.

## 5.8. Override oleh Manager

Flow ini dipakai jika ada mismatch, tetapi manager memutuskan order tetap boleh diserahkan.

Langkah:

1. Buka checker untuk order tersebut.
2. Klik `Override & Complete`.
3. Isi alasan override.
4. Konfirmasi.

Expected outcome:

1. Status order berubah menjadi `Overridden`.
2. Alasan override tersimpan di backend.
3. Sistem menyimpan manager dan waktu override.

Aturan:

1. Hanya user dengan grup `POS Manager` yang boleh melakukan override.
2. Alasan override wajib diisi.

## 5.9. Reopen Checker

Flow ini dipakai jika order yang sudah `Checked` atau `Overridden` perlu dibuka lagi untuk koreksi.

Langkah:

1. Buka checker order yang sudah selesai.
2. Klik `Reopen Checker`.

Expected outcome:

1. Status checker kembali ke `Pending` atau `In Progress`, tergantung progress line yang masih tersimpan.
2. Audit completion atau override sebelumnya dibersihkan.
3. Checked quantity line tetap ada dan bisa dikoreksi.

Aturan:

1. Hanya `POS Manager` yang bisa melakukan reopen.

## 6. Informasi yang Tersimpan di Backend

Pada `POS Order`, backend akan menampilkan informasi berikut:

1. `Online Checker Required`
2. `Online Check Status`
3. `Online Check Progress`
4. `Online Check Note`
5. `Completed At`
6. `Completed By`
7. `Override At`
8. `Override By`
9. `Override Reason`

Lokasi:

1. `Point of Sale > Orders > Orders`
2. Form order pada tab `Online Checker`

Expected outcome:

1. Supervisor atau admin bisa audit progres checker tanpa harus membuka POS.
2. Order bisa difilter atau di-group berdasarkan status checker.

## 7. Skenario Operasional yang Disarankan

### 7.1. Order Online Normal

1. Kasir membuat order.
2. Kasir memilih channel `GrabFood`.
3. Payment diselesaikan.
4. Checker dibuka dari receipt.
5. Semua item di-set sesuai quantity.
6. User klik `Complete Checker`.
7. Order siap diserahkan ke driver.

### 7.2. Order Online Belum Selesai Disiapkan

1. Kasir menyelesaikan payment.
2. Outlet baru menyiapkan sebagian item.
3. User isi quantity parsial.
4. User klik `Save Progress`.
5. Saat item sisa sudah siap, checker dibuka lagi dari `Ticket Screen`.
6. User melengkapi quantity lalu klik `Complete Checker`.

### 7.3. Ada Mismatch tetapi Manager Mengizinkan

1. Payment sudah selesai.
2. Quantity item fisik tidak bisa 100% match order.
3. Kasir tidak bisa `Complete Checker`.
4. Manager membuka checker.
5. Manager klik `Override & Complete`.
6. Manager isi alasan.
7. Order tercatat sebagai `Overridden`.

## 8. Troubleshooting

### 8.1. Tombol checker tidak muncul di Receipt Screen

Periksa:

1. Apakah order sudah berhasil dibayar.
2. Apakah order memakai sales channel yang termasuk `Online Checker Channels`.
3. Apakah order sudah tersimpan ke backend.

### 8.2. Order online tidak masuk status `Pending`

Periksa:

1. Konfigurasi `Online Checker Channels` pada POS config.
2. `Sales Channel` yang dipilih pada order.
3. Jika line memakai override channel, pastikan line online masih ada.

### 8.3. User tidak bisa override atau reopen

Periksa:

1. User harus memiliki grup `POS Manager`.
2. Jika hanya kasir biasa, tombol manager action memang tidak akan tersedia.

### 8.4. Checker tidak menghitung semua line

Periksa:

1. Apakah line tersebut memakai `Item Channel` yang berbeda.
2. Hanya line dengan effective channel yang masuk ke konfigurasi online checker yang akan dihitung.

## 9. Ringkasan Aturan Penting

1. Payment tetap boleh dilakukan sebelum checker.
2. Checker hanya berlaku untuk channel yang dipilih di POS Config.
3. Checker mendukung quantity parsial per line.
4. `Complete Checker` hanya boleh jika quantity full match.
5. `Override & Complete` hanya boleh oleh manager dan wajib alasan.
6. `Reopen Checker` hanya boleh oleh manager.
7. Progress checker bisa dilanjutkan dari `Receipt Screen` atau `Ticket Screen`.
