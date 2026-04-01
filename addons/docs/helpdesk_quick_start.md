# Helpdesk Quick Start (1-Page)

Last updated: 2026-03-31  
Target database: `ksv17-dev`

## 1. Untuk Siapa

Panduan ini untuk user operasional (Agent, Lead, Dispatcher, Customer Success) agar bisa langsung menjalankan proses Helpdesk harian tanpa harus memahami detail teknis modul.

## 2. Alur Harian Paling Penting

1. Buka `Helpdesk > Tickets`.
2. Kerjakan tiket `Open`, utamakan `SLA Watchlist` dan `Unassigned`.
3. Pastikan setiap tiket punya `Category`, `Type`, `Priority`, dan `Assigned User`.
4. Balas customer dari chatter, lalu update stage sesuai progres.
5. Jika butuh persetujuan, klik `Request Approval`.
6. Jika butuh onsite, klik `Schedule Dispatch`.
7. Jika issue berulang, buat `Problem Record`.
8. Jika ada peluang komersial, pakai `Request Sales Follow-up` (jangan convert langsung di tiket).
9. Setelah selesai, close tiket sesuai stage close policy.
10. Cek dashboard di `Helpdesk > Reporting > KPI Overview`.

## 3. Menu yang Paling Sering Dipakai

Operasional:

- `Helpdesk > Tickets`
- `Helpdesk > Calendar`
- `Helpdesk > Timesheets`

Monitoring:

- `Helpdesk > Reporting > KPI Overview`
- `Helpdesk > Reporting > Communication Analytics`
- `Helpdesk > Reporting > Dispatch Board`
- `Helpdesk > Reporting > Approval Requests`
- `Helpdesk > Reporting > Problem Records`
- fokuskan KPI card CSAT risk: `Low CSAT Open`, `Recovery SLA Miss`, `No Follow-up >24h`

Customer and commercial review:

- `Helpdesk > Reporting > Customer Support Overview`
- `Helpdesk > Reporting > Contract Renewals`
- `Helpdesk > Reporting > Renewal Forecast`
- `Helpdesk > Reporting > Service Review Packs`

## 4. Checklist Saat Menangani Tiket

- Data dasar lengkap: `Category`, `Type`, `Priority`, `Assignee`
- Kontrak/coverage sudah benar (`covered` atau `uncovered`)
- Komunikasi customer tercatat rapi
- SLA tidak terlewat
- Approval/dispatch sudah diproses bila diperlukan
- Closing note jelas dan bisa diaudit

## 5. Akses Customer (Portal)

Customer bisa:

- melihat status tiket
- kirim reply/feedback
- upload file
- close/reopen tiket jika diizinkan stage policy

Dari backend, agent bisa:

- klik `Open Public Portal` di form ticket untuk melihat pengalaman customer
- klik `Copy Public Link` untuk copy cepat URL tracking
- klik `Send via Email` untuk kirim link langsung ke kontak customer
- klik `Send via WhatsApp` untuk queue kirim link via WhatsApp
- klik `Refresh Public Link` jika link perlu diganti
- isi `Resolution Summary` saat ticket selesai untuk improve CSAT clarity

## 6. Jika Ada Masalah

- Tidak bisa close tiket: cek field wajib close stage (`Category`, `Type`, `Contact`).
- Portal/API tidak terbuka di local multi-db: pastikan session sudah ke `ksv17-dev`.
- Email notif gagal: minta admin cek konfigurasi sender email.

## 7. Lanjut Belajar

Untuk panduan lengkap skenario end-to-end:

- `helpdesk_user_guide_end_to_end.md`

Untuk panduan khusus customer portal:

- `helpdesk_customer_portal_guide.md`

Untuk daftar fitur lengkap:

- `helpdesk_customization_recap.md`
