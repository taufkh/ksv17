# Panduan Claim Produk Gratis Saat Check-In Member

Dokumen ini adalah panduan singkat dan fokus untuk fitur member claim produk gratis harian saat check-in di POS. Panduan ini ditujukan untuk admin, supervisor outlet, dan kasir.

## 1. Tujuan Fitur

Fitur ini memungkinkan member claim 1 produk gratis per hari saat datang ke outlet dan melakukan check-in melalui kasir.

Pada implementasi saat ini:

1. Claim dilakukan di POS oleh kasir.
2. Member harus dikenali lebih dulu pada order aktif.
3. Produk gratis mengikuti konfigurasi reward harian yang dibuat admin.
4. Setiap member hanya bisa claim 1 kali per hari per company.

## 2. Alur Singkat

Alur operasionalnya adalah:

1. Admin menyiapkan produk reward harian.
2. Kasir membuat order di POS.
3. Kasir scan barcode member atau pilih member secara manual.
4. Kasir menekan tombol `Claim Daily Reward`.
5. Sistem menambahkan produk gratis ke keranjang dengan harga `0`.
6. Order diselesaikan.
7. Sistem mencatat claim agar tidak bisa diulang pada hari yang sama.

## 3. Prasyarat Sebelum Fitur Bisa Dipakai

Sebelum kasir dapat melakukan claim produk gratis, pastikan semua prasyarat berikut sudah terpenuhi.

### 3.1. Customer sudah menjadi member

Periksa di `Contacts`:

1. Kontak customer sudah dicentang `Custom Member`.
2. Tipe membership sudah dipilih `Free` atau `Paid`.
3. Field `Membership Barcode` sudah terisi.

Expected outcome:

1. Customer dikenali sebagai member di POS.
2. Barcode member bisa dipakai saat scan di kasir.

### 3.2. Reward harian sudah dikonfigurasi

Periksa di `Point of Sale > Membership > Daily Reward Config`:

1. Sudah ada record untuk tanggal hari ini.
2. Produk gratis yang akan diklaim sudah dipilih.
3. Record tersebut aktif.
4. Company yang dipilih sesuai dengan outlet atau company POS yang digunakan.

Expected outcome:

1. Saat kasir menekan tombol claim, sistem tahu produk gratis apa yang berlaku hari ini.

### 3.3. Sesi POS sudah aktif

Periksa:

1. Kasir sudah membuka sesi POS.
2. Data member dan reward harian sudah termuat di sesi POS.

Expected outcome:

1. Tombol claim bisa dipakai dari layar produk POS.

## 4. Langkah Admin Menyiapkan Produk Gratis Harian

### 4.1. Membuat konfigurasi reward

Langkah:

1. Buka `Point of Sale > Membership > Daily Reward Config`.
2. Klik `New`.
3. Isi `Date` dengan tanggal reward berlaku.
4. Isi `Company` sesuai company outlet yang akan menjalankan promo.
5. Pilih `Product` yang akan diberikan gratis.
6. Centang `Active`.
7. Simpan.

Expected outcome:

1. Produk yang dipilih menjadi reward harian untuk tanggal tersebut.
2. Kasir dapat claim produk itu untuk member yang eligible.

Catatan:

1. Secara operasional, disarankan hanya ada satu reward aktif per tanggal per company.
2. Jika tidak ada reward aktif, kasir tidak akan bisa claim produk gratis.

## 5. Langkah Kasir Melakukan Check-In dan Claim

### 5.1. Membuat order aktif

Langkah:

1. Buka POS.
2. Buat order baru atau gunakan order aktif yang masih kosong.

Expected outcome:

1. Order siap dipakai untuk proses check-in member.

### 5.2. Mengaitkan member ke order

Ada dua cara.

Cara 1, scan barcode member:

1. Scan barcode member di POS.

Expected outcome:

1. Customer pada order aktif otomatis berubah menjadi member yang discan.
2. Informasi member tampil di POS.

Cara 2, pilih manual:

1. Klik pilihan customer pada order.
2. Cari dan pilih customer member.

Expected outcome:

1. Order aktif sekarang terhubung ke member tersebut.

### 5.3. Claim produk gratis

Langkah:

1. Pastikan member sudah menempel pada order aktif.
2. Di layar produk POS, klik tombol `Claim Daily Reward`.
3. Tunggu validasi dari sistem.

Expected outcome jika valid:

1. Produk reward harian otomatis masuk ke keranjang.
2. Harga line produk reward menjadi `0`.
3. Order ditandai sebagai order yang membawa claim harian.

### 5.4. Selesaikan transaksi

Langkah:

1. Setelah produk reward masuk ke keranjang, lanjutkan proses order.
2. Jika order hanya untuk claim produk gratis, selesaikan sesuai alur outlet.
3. Jika ada produk lain yang dibeli member, lanjutkan transaksi seperti biasa.

Expected outcome:

1. Claim tersimpan saat order tervalidasi ke backend.
2. Sistem membuat log claim harian.
3. Member tidak bisa claim lagi pada hari yang sama.

## 6. Hasil yang Harus Terlihat di POS

Saat fitur berjalan normal, kasir akan melihat hal berikut:

1. Customer member tampil pada order aktif.
2. Badge atau informasi membership muncul di POS.
3. Produk reward harian masuk ke cart setelah tombol claim ditekan.
4. Nilai produk reward di cart adalah `0`.
5. Jika order selesai, claim dianggap sudah dipakai untuk hari itu.

## 7. Kondisi Saat Claim Harus Ditolak

Sistem akan menolak claim dalam kondisi berikut:

1. Order belum memiliki customer member.
2. Tidak ada reward aktif untuk hari ini.
3. Member sudah pernah claim pada tanggal yang sama.
4. Produk reward yang diklaim tidak sesuai dengan konfigurasi aktif saat order divalidasi.

Expected outcome:

1. POS menampilkan error.
2. Produk gratis tidak ditambahkan ke keranjang.
3. Tidak ada claim log baru yang dibuat.

## 8. Contoh Skenario Operasional

### 8.1. Skenario berhasil

Kondisi:

1. Hari ini admin mengaktifkan reward `Donat Glaze`.
2. Member datang ke outlet.
3. Kasir scan barcode member.
4. Kasir klik `Claim Daily Reward`.

Expected outcome:

1. `Donat Glaze` masuk ke cart dengan harga `0`.
2. Order bisa dilanjutkan atau langsung diselesaikan.
3. Setelah order selesai, member tercatat sudah claim hari ini.

### 8.2. Skenario gagal karena sudah claim

Kondisi:

1. Member yang sama sudah claim pada pagi hari.
2. Member datang lagi dan kasir mencoba claim ulang.

Expected outcome:

1. Sistem menolak claim kedua.
2. POS menampilkan pesan bahwa reward hari ini sudah pernah diklaim.

### 8.3. Skenario gagal karena admin belum set reward

Kondisi:

1. Hari ini belum ada `Daily Reward Config` aktif.
2. Kasir mencoba claim untuk member.

Expected outcome:

1. Sistem menolak claim.
2. Tidak ada produk gratis yang masuk ke cart.

## 9. Cara Cek Bukti Claim di Backend

Untuk audit, admin dapat memeriksa claim yang sudah terjadi.

Langkah:

1. Buka `Point of Sale > Membership > Daily Claim Logs`.
2. Cari nama member atau tanggal transaksi.

Expected outcome:

1. Terlihat siapa yang claim.
2. Terlihat tanggal claim.
3. Terlihat produk yang diberikan.
4. Terlihat order POS terkait jika ada.

## 10. Troubleshooting Singkat

### 10.1. Tombol claim ditekan tapi tidak ada produk masuk

Periksa:

1. Apakah customer pada order benar-benar member.
2. Apakah reward harian aktif untuk tanggal hari ini.
3. Apakah session POS sudah memuat data terbaru.

Tindakan:

1. Reload POS jika perlu.
2. Periksa ulang konfigurasi reward.

### 10.2. Barcode member discan tapi customer tidak terpilih

Periksa:

1. Barcode member di kontak.
2. Status `Custom Member`.
3. Apakah data member sudah dimuat di POS.

### 10.3. Member bilang belum claim, tapi sistem menolak

Periksa:

1. `Daily Claim Logs` untuk tanggal hari ini.
2. Order POS yang terkait.
3. Company outlet yang digunakan saat claim.

## 11. Ringkasan Praktis untuk Kasir

Urutan yang paling sederhana untuk kasir adalah:

1. Buat order.
2. Scan barcode member.
3. Klik `Claim Daily Reward`.
4. Pastikan produk gratis masuk dengan harga `0`.
5. Selesaikan order.

Kalau muncul error:

1. Cek apakah member sudah pernah claim hari ini.
2. Cek apakah admin sudah membuat reward aktif hari ini.
3. Jika tetap gagal, laporkan ke supervisor untuk cek `Daily Claim Logs`.
