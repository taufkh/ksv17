# Customer Portal Guide

Last updated: 2026-03-31  
Target database: `ksv17-dev`

## 1. Tujuan

Panduan ini untuk customer/client agar bisa menggunakan portal Helpdesk secara mandiri:

- cek status tiket
- kirim update
- upload lampiran
- close atau reopen tiket (jika diizinkan)
- kirim feedback/rating

## 2. Dua Cara Akses Portal

### A. Portal Login (`/my/tickets`)

Dipakai jika customer punya akun portal.

Bisa dilakukan:

- lihat daftar semua tiket milik akun/customer
- cari tiket dan cek detail
- buka histori komunikasi
- kirim balasan dari halaman tiket

### B. Public Tracking Link (`/helpdesk/track/<token>`)

Dipakai jika customer menerima link tracking dari tim support.

Bisa dilakukan:

- akses detail tiket tanpa masuk ke backend internal
- update tiket dari halaman publik
- close/reopen tiket sesuai aturan stage
- request escalation (jika tim support mengaktifkan fitur escalation)
- kirim feedback langsung

## 3. End-to-End Skenario Customer

### Scenario 1: Create Ticket and Follow Progress

1. Buka portal customer (`My Tickets`) atau link publik yang diberikan.
2. Buat tiket baru (jika menu create tersedia) atau mulai dari tiket yang sudah ada.
3. Isi subject/description dengan detail masalah:
   tanggal kejadian, dampak, dan langkah yang sudah dicoba.
4. Cek halaman tiket secara berkala untuk melihat:
   stage, SLA deadline, assignee, dan update terakhir.

Hasil yang diharapkan:

- customer bisa memonitor progres tanpa perlu tanya manual berkali-kali.

### Scenario 2: Send Update with Attachment

1. Buka detail tiket.
2. Isi pesan update yang jelas (contoh: error terbaru, hasil test ulang, urgency).
3. Upload file pendukung (screenshot, log, dokumen).
4. Submit update.

Tips:

- kirim file relevan agar investigasi lebih cepat
- jika upload ditolak, cek format/ukuran file sesuai info di halaman portal

Hasil yang diharapkan:

- tim support menerima konteks lengkap dan bisa memberi respon lebih cepat.

### Scenario 3: Close Ticket from Customer Side

1. Pastikan solusi sudah diterima dan issue sudah selesai.
2. Buka tiket, pilih aksi close (jika tombol close muncul).
3. Konfirmasi close.

Catatan:

- tombol close hanya muncul jika stage policy mengizinkan close dari portal.

Hasil yang diharapkan:

- tiket berpindah ke status selesai dengan jejak audit yang jelas.

### Scenario 4: Reopen Ticket if Issue Returns

1. Jika masalah muncul lagi setelah close, buka tiket via portal.
2. Klik aksi `Reopen` (jika tersedia).
3. Tambahkan update singkat tentang issue yang kembali muncul.

Catatan:

- reopen hanya tersedia untuk stage tertentu yang diizinkan sistem.

Hasil yang diharapkan:

- tiket aktif kembali tanpa harus membuat tiket baru.

### Scenario 5: Give Feedback and Rating

1. Setelah tiket ditutup, isi feedback/rating dari halaman portal atau link rating.
2. Jelaskan pengalaman secara spesifik:
   kecepatan respon, kualitas solusi, dan saran perbaikan.

Hasil yang diharapkan:

- masukan customer masuk ke evaluasi kualitas support.

### Scenario 6: Request Escalation for Urgent Impact

1. Buka tiket di public tracking page.
2. Klik `Request Escalation`.
3. Isi alasan eskalasi dengan dampak bisnis terkini.
4. Pilih preferred channel (email / WhatsApp / phone) jika diperlukan.
5. Pilih preferred callback time lalu submit.

Catatan:

- escalation request memiliki cooldown window untuk mencegah spam request berulang.
- jika baru saja request escalation, customer perlu menunggu sesuai cooldown sebelum submit lagi.

Hasil yang diharapkan:

- tim support menerima sinyal prioritas tinggi dan follow-up activity internal otomatis dibuat.

## 4. Informasi yang Perlu Diperhatikan Customer

- Ticket Number:
  selalu sertakan nomor tiket saat komunikasi di luar portal.
- SLA Deadline:
  menunjukkan target waktu penanganan.
- Last Update:
  membantu cek kapan terakhir ada aktivitas di tiket.
- Conversation History:
  gunakan histori ini agar diskusi tidak terputus.

## 5. Best Practice untuk Customer

1. Gunakan satu tiket untuk satu issue utama.
2. Beri detail langkah reproduksi error.
3. Lampirkan bukti yang relevan.
4. Hindari membuat tiket duplikat untuk kasus yang sama.
5. Pakai reply pada tiket yang sama untuk update lanjutan.

## 6. FAQ Singkat

### Kenapa saya tidak bisa close tiket?

Kemungkinan stage policy untuk tiket tersebut tidak mengizinkan close dari portal.

### Kenapa saya tidak bisa reopen tiket?

Reopen hanya tersedia pada kondisi/stage tertentu. Jika tombol tidak ada, minta tim support untuk buka ulang.

### Kenapa file upload ditolak?

Biasanya karena format file tidak termasuk daftar yang diizinkan atau ukuran file melebihi batas.

### Kenapa link portal tidak bisa diakses?

Kemungkinan link sudah expired atau direvoke. Minta tim support kirim link baru.

## 7. Kapan Harus Hubungi Support Langsung

Hubungi support langsung jika:

- isu berdampak kritikal ke operasional
- tidak ada update dalam waktu yang lama
- akses portal bermasalah terus-menerus

Saat menghubungi support, sertakan:

- nomor tiket
- ringkasan dampak bisnis
- waktu kejadian terbaru

## 8. Referensi Tambahan

- `helpdesk_quick_start.md`
- `helpdesk_user_guide_end_to_end.md`
