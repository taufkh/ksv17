# Panduan Pengguna POS Membership

Dokumen ini menjelaskan cara penggunaan modul `pos_membership` pada Odoo 17, mulai dari konfigurasi awal, pengelolaan member, penggunaan di POS, sampai akses portal member. Panduan ini ditulis untuk admin, supervisor POS, dan kasir.

## 1. Tujuan Modul

Modul `pos_membership` menambahkan fitur membership terintegrasi ke POS dengan cakupan berikut:

1. Member bertipe `Free` atau `Paid`.
2. Saldo deposit yang bisa di-top up dan dipakai sebagai metode pembayaran di POS.
3. Poin loyalitas yang dihitung otomatis dari transaksi yang memenuhi syarat.
4. Reward harian berupa produk gratis yang hanya bisa diklaim 1 kali per hari.
5. Portal member untuk melihat barcode, saldo deposit, poin, dan histori mutasi.

## 2. Ringkasan Hasil yang Diharapkan

Jika modul sudah dikonfigurasi dengan benar, hasil penggunaan yang diharapkan adalah:

1. Kontak yang ditandai sebagai member otomatis memiliki barcode member unik.
2. Kasir bisa mengenali member dari barcode dan mengaitkan member ke order aktif di POS.
3. Top up deposit tercatat di ledger deposit sebagai mutasi masuk.
4. Pembayaran dengan deposit tercatat di ledger deposit sebagai mutasi keluar dan tidak bisa melebihi saldo aktual.
5. Poin otomatis bertambah setelah transaksi eligible tervalidasi di backend.
6. Produk top up deposit dan reward gratis harian tidak menghasilkan poin.
7. Claim reward harian kedua pada hari yang sama akan ditolak.
8. Portal member menampilkan saldo deposit, total poin, barcode, reward aktif, dan histori mutasi terbaru.

## 3. Peran yang Umum Menggunakan Modul

1. Admin atau supervisor untuk konfigurasi awal dan audit ledger.
2. Admin atau customer service untuk menandai customer sebagai member.
3. Kasir untuk scan member, top up, claim reward, dan pembayaran deposit.
4. Member portal untuk melihat data membership secara mandiri.

## 4. Konfigurasi Awal

### 4.1. Konfigurasi metode pembayaran deposit

Langkah:

1. Buka menu `Point of Sale > Configuration > Payment Methods`.
2. Buka atau buat payment method yang akan dipakai untuk deposit.
3. Aktifkan centang `Is Membership Deposit`.
4. Simpan.

Expected outcome:

1. Payment method tersebut dikenali sistem sebagai metode pembayaran deposit member.
2. Saat dipakai di POS, nominal deposit akan divalidasi terhadap saldo member.

### 4.2. Konfigurasi membership di POS Settings

Langkah:

1. Buka menu `Point of Sale > Configuration > Settings`.
2. Cari blok pengaturan `Membership`.
3. Isi field berikut:
   - `Barcode Prefix`: prefix barcode member, contoh `MBR`.
   - `Point Conversion`: nominal belanja per poin dan jumlah poin yang diperoleh.
   - `Top Up Product`: produk POS khusus untuk top up deposit.
   - `Deposit Payment Method`: payment method yang sudah ditandai sebagai deposit.
   - `Load Members in POS`: aktifkan jika data field membership ingin dimuat ke sesi POS.
4. Simpan pengaturan.

Expected outcome:

1. Member baru akan menggunakan prefix barcode sesuai setting company.
2. POS mengetahui produk mana yang dianggap top up deposit.
3. POS mengetahui payment method mana yang mewakili deposit member.
4. Konversi poin berlaku pada transaksi POS berikutnya.

### 4.3. Konfigurasi reward harian

Langkah:

1. Buka menu `Point of Sale > Membership > Daily Reward Config`.
2. Buat record baru.
3. Isi:
   - `Date`: tanggal reward berlaku.
   - `Company`: company yang berlaku.
   - `Product`: produk gratis yang bisa diklaim.
   - `Active`: aktifkan.
4. Simpan.

Expected outcome:

1. Pada tanggal tersebut, POS dapat menawarkan produk reward harian.
2. Hanya satu reward aktif per company per tanggal yang sebaiknya digunakan secara operasional agar tidak membingungkan kasir.

## 5. Menyiapkan Customer Menjadi Member

Langkah:

1. Buka menu `Contacts`.
2. Buka customer yang akan dijadikan member.
3. Masuk ke tab `Membership`.
4. Aktifkan `Custom Member`.
5. Pilih `Membership Type` menjadi `Free` atau `Paid`.
6. Simpan.

Expected outcome:

1. Field `Membership Barcode` otomatis terisi jika sebelumnya kosong.
2. Field `Deposit Balance` dan `Total Points` tampil sebagai nilai read-only.
3. Customer sekarang dapat dikenali sebagai member di POS.

Catatan:

1. Pada implementasi saat ini, tipe `Free` dan `Paid` berfungsi sebagai label status dan segmentasi.
2. Benefit transaksi saat ini sama untuk kedua tipe tersebut.

## 6. Mengaktifkan Akses Portal Member

Langkah:

1. Pastikan kontak sudah menjadi member.
2. Gunakan flow standar Odoo untuk memberikan akses portal ke kontak tersebut.
3. Setelah user portal aktif, cek kembali tab `Membership` pada kontak.

Expected outcome:

1. Field `Portal Access Enabled` akan bernilai aktif secara otomatis.
2. Member dapat login melalui halaman `/member/login`.
3. Member dapat mengakses halaman `/member/dashboard` setelah login.

Catatan:

1. Akses portal bukan dibuat otomatis saat customer ditandai sebagai member.
2. Aktivasi portal mengikuti flow invite portal standar Odoo.

## 7. Penggunaan di POS

### 7.1. Mengenali member dari barcode

Langkah:

1. Buka sesi POS seperti biasa.
2. Saat ada order aktif, scan barcode member.
3. Pastikan barcode yang discan sesuai nilai `Membership Barcode` pada kontak.

Expected outcome:

1. Customer pada order aktif otomatis berubah menjadi member yang discan.
2. POS menampilkan informasi member seperti tipe membership, saldo deposit, dan total poin.
3. Jika barcode tidak ditemukan, POS menampilkan pesan error.

### 7.2. Memilih customer member secara manual

Langkah:

1. Pada order POS, pilih customer secara manual dari daftar customer.
2. Pilih customer yang sudah ditandai sebagai member.

Expected outcome:

1. Area informasi member di POS muncul untuk order tersebut.
2. Data yang tampil bersifat informatif dan dibaca dari data member yang dimuat ke POS.

### 7.3. Top up deposit

Langkah:

1. Pastikan order aktif sudah memiliki customer member.
2. Tambahkan `Top Up Product` ke keranjang.
3. Sesuaikan harga atau nominal top up sesuai proses operasional outlet.
4. Lanjutkan ke pembayaran dan selesaikan order.

Expected outcome:

1. Setelah order tervalidasi, sistem membuat mutasi `in` pada `Deposit Ledger`.
2. Nilai `Deposit Balance` member bertambah sesuai nominal top up.
3. Nominal top up tidak dihitung sebagai dasar perolehan poin.
4. Struk dapat menampilkan nilai top up dan saldo deposit terbaru.

Catatan:

1. Praktik yang disarankan adalah hanya melakukan top up saat order sudah memiliki member.
2. Produk top up dipakai sebagai penanda transaksi deposit masuk, bukan order kosong.

### 7.4. Pembayaran dengan deposit

Langkah:

1. Pastikan order aktif memiliki customer member.
2. Tambahkan produk belanja normal ke keranjang.
3. Masuk ke layar pembayaran.
4. Pilih payment method deposit yang sudah ditandai `Is Membership Deposit`.
5. Masukkan nominal yang ingin dibayar dari deposit.
6. Selesaikan sisa pembayaran dengan metode lain jika diperlukan.

Expected outcome:

1. Sistem menolak penggunaan payment method deposit jika order belum memiliki member.
2. Sistem menolak nominal deposit yang lebih besar dari saldo tersedia atau lebih besar dari sisa tagihan.
3. Setelah order sync, sistem membuat mutasi `out` pada `Deposit Ledger`.
4. Saldo deposit member berkurang sesuai nominal yang digunakan.
5. Transaksi campuran cash plus deposit tetap menghasilkan pencatatan ledger yang benar.

### 7.5. Earn points otomatis

Langkah:

1. Lakukan transaksi POS normal menggunakan customer member.
2. Pastikan transaksi berisi produk eligible.
3. Finalisasi order.

Expected outcome:

1. Sistem menghitung poin berdasarkan setting company:
   - `Amount per Point`
   - `Points Earned`
2. Poin hanya dihitung dari subtotal produk eligible.
3. Baris top up deposit tidak ikut menghasilkan poin.
4. Produk reward gratis harian tidak ikut menghasilkan poin.
5. Setelah order tervalidasi, sistem membuat mutasi `earned` di `Point Ledger`.
6. `Total Points` member bertambah sesuai hasil perhitungan.

Contoh:

1. Jika setting adalah `Rp10.000 = 1 poin` dan transaksi eligible adalah `Rp55.000`, maka member mendapat `5 poin`.
2. Jika transaksi hanya berisi top up deposit, maka member mendapat `0 poin`.

### 7.6. Claim reward harian

Langkah:

1. Pastikan order aktif memiliki customer member.
2. Pastikan admin sudah menyiapkan `Daily Reward Config` aktif untuk tanggal hari ini.
3. Pada layar produk POS, klik tombol `Claim Daily Reward`.
4. Jika valid, lanjutkan order dan selesaikan transaksi.

Expected outcome:

1. Jika member belum claim hari ini, produk reward otomatis masuk ke cart dengan harga `0`.
2. Order ditandai membawa metadata claim harian.
3. Saat order tervalidasi di backend, sistem membuat record pada `Daily Claim Logs`.
4. Jika member mencoba claim kedua di tanggal yang sama, sistem menolak dengan error.
5. Jika tidak ada reward aktif untuk hari ini, sistem menolak claim.

Catatan:

1. Reward harian dikonsumsi di POS, bukan dari portal.
2. Proteksi claim ganda tetap dijalankan di backend untuk mencegah bentrok antar sesi POS.

### 7.7. Informasi pada struk

Setelah transaksi membership selesai, expected outcome pada struk adalah:

1. Identitas member dapat ditampilkan.
2. Nilai deposit yang dipakai pada transaksi dapat ditampilkan.
3. Nilai top up pada transaksi dapat ditampilkan jika ada.
4. Saldo deposit terbaru setelah transaksi dapat ditampilkan.
5. Poin yang diperoleh pada transaksi dapat ditampilkan.
6. Total poin terbaru member dapat ditampilkan.

## 8. Audit dan Monitoring di Backend

### 8.1. Deposit Ledger

Lokasi menu:

1. `Point of Sale > Membership > Deposit Ledger`

Fungsi:

1. Melihat semua mutasi deposit masuk dan keluar.
2. Audit sumber mutasi seperti `topup`, `usage`, atau `refund`.
3. Menelusuri referensi order POS terkait.

Expected outcome:

1. Setiap top up deposit yang valid muncul sebagai mutasi `in`.
2. Setiap pemakaian deposit di POS muncul sebagai mutasi `out`.
3. Balance member konsisten dengan akumulasi ledger posted.

### 8.2. Point Ledger

Lokasi menu:

1. `Point of Sale > Membership > Point Ledger`

Fungsi:

1. Melihat histori poin earned dan redeemed.
2. Audit referensi order yang menghasilkan poin.

Expected outcome:

1. Transaksi POS eligible menambah baris `earned`.
2. Penyesuaian atau penukaran poin menambah baris `redeemed` bila digunakan oleh proses backend.
3. Total poin member konsisten dengan akumulasi ledger.

### 8.3. Daily Claim Logs

Lokasi menu:

1. `Point of Sale > Membership > Daily Claim Logs`

Fungsi:

1. Melihat siapa yang sudah claim reward harian.
2. Menjadi bukti audit bahwa satu member hanya claim sekali per hari per company.

Expected outcome:

1. Setiap claim reward harian yang valid menghasilkan satu record log.
2. Tidak ada duplikasi claim untuk member, tanggal, dan company yang sama.

## 9. Portal Member

### 9.1. Login member

Langkah:

1. Pastikan member sudah punya user portal aktif.
2. Buka URL `/member/login`.
3. Masukkan email dan password user portal.
4. Klik tombol masuk.

Expected outcome:

1. Member diarahkan ke `/member/dashboard`.
2. Non-member atau user tanpa hak akses portal member tidak boleh melihat dashboard ini.

### 9.2. Isi dashboard member

Data yang ditampilkan pada dashboard:

1. Nama member.
2. Tipe membership.
3. Barcode member.
4. Saldo deposit terkini.
5. Total poin terkini.
6. Status akses portal.
7. Tanggal check-in terakhir jika ada.
8. Reward aktif yang relevan.
9. Histori deposit terbaru.
10. Histori poin terbaru.

Expected outcome:

1. Member bisa melihat barcode identitas langsung di browser.
2. Member bisa memeriksa saldo deposit tanpa bertanya ke kasir.
3. Member bisa memeriksa total poin yang sudah terkumpul.
4. Member bisa melihat histori mutasi terbaru untuk verifikasi sederhana.

## 10. Skenario Operasional yang Disarankan

### 10.1. Skenario member baru

1. Admin membuat atau membuka kontak customer.
2. Admin mengaktifkan `Custom Member`.
3. Sistem membuat barcode member unik.
4. Jika perlu, admin memberi akses portal.

Expected outcome:

1. Customer langsung siap dipakai di POS sebagai member.
2. Customer bisa menerima top up deposit, poin, dan reward harian.

### 10.2. Skenario top up lalu belanja

1. Kasir memilih member pada order.
2. Kasir menambahkan produk top up deposit.
3. Order dibayar dan selesai.
4. Kasir membuat order baru atau melanjutkan order lain untuk belanja.
5. Kasir memakai payment method deposit saat checkout.

Expected outcome:

1. Top up menambah saldo deposit member.
2. Penggunaan deposit mengurangi saldo deposit member.
3. Kedua mutasi dapat dilihat di Deposit Ledger.

### 10.3. Skenario claim reward harian

1. Admin menyiapkan reward aktif untuk hari ini.
2. Kasir memilih atau scan member.
3. Kasir menekan tombol claim reward.
4. Produk gratis masuk ke cart.
5. Order diselesaikan.

Expected outcome:

1. Member menerima produk gratis dengan harga `0`.
2. Claim tercatat di `Daily Claim Logs`.
3. Claim kedua pada hari yang sama ditolak.

## 11. Troubleshooting Singkat

### 11.1. Barcode member tidak terbaca di POS

Periksa:

1. Customer benar-benar ditandai sebagai `Custom Member`.
2. Field `Membership Barcode` terisi.
3. `Load Members in POS` aktif di pengaturan POS.
4. Sesi POS direload setelah perubahan konfigurasi besar.

Expected outcome setelah perbaikan:

1. Scan barcode akan mengaitkan member ke order aktif.

### 11.2. Payment method deposit tidak bisa dipakai

Periksa:

1. Payment method sudah dicentang `Is Membership Deposit`.
2. Payment method tersebut dipilih pada setting company sebagai `Deposit Payment Method`.
3. Order aktif sudah memiliki customer member.
4. Saldo deposit member mencukupi.

Expected outcome setelah perbaikan:

1. Deposit bisa dipakai sampai batas saldo tersedia dan sisa due.

### 11.3. Poin tidak bertambah

Periksa:

1. Konfigurasi `Amount per Point` dan `Points Earned` sudah benar.
2. Transaksi memang memiliki nilai eligible di luar produk top up dan reward gratis.
3. Order sudah benar-benar tervalidasi ke backend.

Expected outcome setelah perbaikan:

1. Point Ledger bertambah dan total poin member ikut naik.

### 11.4. Claim reward ditolak

Periksa:

1. Ada reward aktif untuk tanggal hari ini.
2. Member belum pernah claim hari ini.
3. Order aktif sudah memakai customer member.

Expected outcome setelah perbaikan:

1. Produk reward bisa ditambahkan ke cart dengan harga `0`.

### 11.5. Member tidak bisa akses dashboard

Periksa:

1. Kontak sudah bertipe member.
2. User portal aktif dan terkait ke partner yang benar.
3. Login dilakukan memakai akun portal yang benar.

Expected outcome setelah perbaikan:

1. Member bisa login ke `/member/login` dan masuk ke `/member/dashboard`.

## 12. Batasan Implementasi Saat Ini

1. Tipe `Free` dan `Paid` belum dibedakan benefit transaksinya.
2. Reward harian diklaim melalui POS, bukan self-service dari portal.
3. Akses portal memakai flow standar invite portal Odoo.
4. Ledger adalah sumber audit utama untuk saldo deposit dan total poin.
5. Top up deposit mengikuti pola produk POS khusus, bukan transaksi kosong.

## 13. Checklist Verifikasi Setelah Go-Live

Gunakan checklist berikut setelah modul dipasang di database target:

1. Buat satu customer member dan pastikan barcode otomatis terisi.
2. Buat satu payment method deposit dan pastikan field `Is Membership Deposit` aktif.
3. Set `Top Up Product` dan `Deposit Payment Method` di konfigurasi POS.
4. Jalankan satu transaksi top up dan cek `Deposit Ledger`.
5. Jalankan satu transaksi pembayaran deposit dan cek saldo berkurang.
6. Jalankan satu transaksi belanja eligible dan cek `Point Ledger`.
7. Buat satu reward harian dan lakukan claim pertama.
8. Coba claim kedua pada hari yang sama dan pastikan sistem menolak.
9. Aktifkan portal untuk satu member dan cek dashboard member.

Jika semua langkah di atas berhasil, maka modul siap digunakan secara operasional.
