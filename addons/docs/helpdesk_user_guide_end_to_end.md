# Helpdesk User Guide (End-to-End Scenarios)

Last updated: 2026-03-31  
Target database: `ksv17-dev`

## 1. Tujuan Dokumen

Dokumen ini menjelaskan cara menggunakan custom Helpdesk berdasarkan alur kerja nyata dari ujung ke ujung (end-to-end), bukan hanya daftar fitur per modul.

Fokus utama:

- siapa melakukan apa
- menu yang dipakai di tiap langkah
- modul custom yang terlibat
- output yang diharapkan

## 2. Peran Pengguna

Peran yang dipakai dalam skenario:

- `Customer / Client`: akses portal publik atau portal login
- `Support Agent`: triage, reply, assignment, close
- `Support Lead / Manager`: SLA monitor, escalation, approval, KPI review
- `Approver`: approve/reject exception request
- `Dispatcher / Field Engineer`: jadwalkan dan eksekusi onsite
- `Finance`: invoice dari support effort
- `Sales / Account Manager`: follow-up handoff komersial
- `Customer Success Manager`: playbook, renewal follow-up, executive review
- `System Admin`: konfigurasi rules, API, templates, schedule

## 3. Peta Menu Cepat

Menu operasional:

- `Helpdesk > Tickets`
- `Helpdesk > Calendar`
- `Helpdesk > Timesheets`

Menu reporting utama:

- `Helpdesk > Reporting > KPI Overview`
- `Helpdesk > Reporting > Communication Analytics`
- `Helpdesk > Reporting > Problem Records`
- `Helpdesk > Reporting > Release Notes`
- `Helpdesk > Reporting > Dispatch Board`
- `Helpdesk > Reporting > Field Service Reports`
- `Helpdesk > Reporting > Approval Requests`
- `Helpdesk > Reporting > Sales Handoffs`
- `Helpdesk > Reporting > Customer Support Overview`
- `Helpdesk > Reporting > Contract Renewals`
- `Helpdesk > Reporting > Renewal Overview`
- `Helpdesk > Reporting > Renewal Analytics`
- `Helpdesk > Reporting > Renewal Forecast`
- `Helpdesk > Reporting > Service Review Packs`
- `Helpdesk > Reporting > Service Review Distribution`
- `Helpdesk > Reporting > Customer Success Playbooks`

Menu konfigurasi utama:

- `Helpdesk > Configuration > Escalation Rules`
- `Helpdesk > Configuration > WhatsApp Templates`
- `Helpdesk > Configuration > Support Contracts`
- `Helpdesk > Configuration > Support Assets`
- `Helpdesk > Configuration > Renewal Targets`

## 4. Prasyarat Setup (One-Time)

Lakukan setup ini sebelum masuk operasi harian:

1. Pastikan team, stage, category, type, channel, assignment method, dan SLA policy sudah aktif.
2. Set kontrak support customer di `Support Contracts`.
3. Map asset yang dicakup kontrak di `Support Assets`.
4. Atur escalation rule di `Escalation Rules`.
5. Atur WhatsApp template dan mode provider (sandbox/live).
6. Atur API token di Helpdesk settings.
7. Pastikan stage close punya aturan `close_from_portal` jika ingin customer bisa close/reopen dari portal.

## 5. Skenario End-to-End

### Scenario A: Customer Ticket from Portal to Resolution

Use case:

- Customer melaporkan issue dari portal, support memproses sampai close dan feedback.

Langkah:

1. Customer buka link publik ticket `Open Public Portal` atau portal `My Tickets`.
2. Customer kirim update/reply via portal (`/helpdesk/track/<token>/reply`).
3. Agent buka `Helpdesk > Tickets`, validasi `category`, `type`, `priority`, `assignee`.
4. Sistem evaluasi SLA dan escalation otomatis berdasarkan rule.
5. Agent kirim update status, lalu close ticket.
6. Customer beri feedback/rating dari portal.

Modul yang terlibat:

- `helpdesk_custom_portal`
- `helpdesk_custom_customer_communication_log`
- `helpdesk_custom_escalation`
- `helpdesk_custom_whatsapp`
- `helpdesk_custom_kpi`

Hasil yang diharapkan:

- ticket timeline lengkap
- komunikasi portal tercatat di communication log
- SLA status terlihat di ticket dan KPI
- rating masuk ke analytics

### Scenario B: Onsite Issue with Approval and Dispatch

Use case:

- Gangguan tidak bisa diselesaikan remote, butuh approval onsite dan visit engineer.

Langkah:

1. Agent buka ticket, klik `Request Approval`.
2. Approver proses request di `Helpdesk > Reporting > Approval Requests`.
3. Jika approved, agent/lead klik `Schedule Dispatch`.
4. Dispatcher isi jadwal, engineer, lokasi, kontak site.
5. Engineer update execution checklist, timestamps, evidence.
6. Engineer/lead buat `Field Service Report`.
7. Customer acknowledgement report.
8. Agent close ticket jika outcome sudah selesai.

Modul yang terlibat:

- `helpdesk_custom_approval`
- `helpdesk_custom_dispatch`
- `helpdesk_custom_dispatch_execution`
- `helpdesk_custom_field_service_report`
- `helpdesk_custom_asset_coverage`

Hasil yang diharapkan:

- approval traceable
- dispatch lifecycle dan bukti onsite terdokumentasi
- service report formal tersedia

### Scenario C: Recurring Incident to Problem and Release Management

Use case:

- Issue berulang lintas ticket perlu RCA, known error, dan komunikasi fix rollout.

Langkah:

1. Dari ticket utama, klik `Create Problem`.
2. Link ticket lain yang relevan ke problem record.
3. Isi RCA, workaround, dan fix plan.
4. Buat release note untuk fix yang dipublish.
5. Link release note ke ticket/problem/knowledge article.
6. Publish knowledge article untuk internal atau portal (jika sudah siap).

Modul yang terlibat:

- `helpdesk_custom_problem_management`
- `helpdesk_custom_release_note_tracking`
- `helpdesk_custom_knowledge`
- `helpdesk_custom_knowledge_portal`

Hasil yang diharapkan:

- known error management terstruktur
- customer update fix lebih konsisten
- kasus berulang berkurang karena knowledge reuse

### Scenario D: Contract Coverage and Invoice from Support Work

Use case:

- Ticket harus mengikuti entitlement kontrak dan effort ditagih bila billable.

Langkah:

1. Saat ticket dibuat, sistem match `Support Contract` berdasarkan customer/team.
2. Agent isi timesheet dan time type untuk effort support.
3. Monitor `remaining hours` kontrak di ticket/contract form.
4. Jalankan wizard invoice dari ticket atau batch invoicing.
5. Finance review dan post invoice.

Modul yang terlibat:

- `helpdesk_custom_contract`
- `helpdesk_custom_asset_coverage`
- `helpdesk_custom_invoice`

Hasil yang diharapkan:

- entitlement jelas (`covered` vs `uncovered`)
- jam support terukur
- billing traceable ke ticket/timesheet

### Scenario E: Support to Sales Handoff (Separated Flow)

Use case:

- Ada peluang komersial dari ticket, tapi tidak langsung convert di form ticket.

Langkah:

1. Agent klik `Request Sales Follow-up` dari ticket.
2. Sales review di `Helpdesk > Reporting > Sales Handoffs`.
3. Sales approve/reject handoff.
4. Jika valid, convert ke opportunity dari record handoff.

Modul yang terlibat:

- `helpdesk_custom_sales_handoff`

Hasil yang diharapkan:

- helpdesk tetap fokus support
- flow komersial tetap tersedia tapi terpisah

### Scenario F: Executive Service Review and Renewal Planning

Use case:

- Monthly/quarterly service review untuk customer strategis dan perencanaan renewal.

Langkah:

1. Cek health customer di `Customer Support Overview`.
2. Review KPI dan communication trend.
3. Generate `Service Review Pack` untuk periode review.
4. Aktifkan `Service Review Distribution` agar report terkirim otomatis.
5. Monitor `Contract Renewals`, `Renewal Analytics`, dan `Renewal Forecast`.
6. Jalankan `Customer Success Playbooks` untuk proactive actions.

Modul yang terlibat:

- `helpdesk_custom_customer_360`
- `helpdesk_custom_kpi`
- `helpdesk_custom_communication_analytics`
- `helpdesk_custom_service_review_pack`
- `helpdesk_custom_service_review_distribution`
- `helpdesk_custom_contract_renewal`
- `helpdesk_custom_contract_renewal_analytics`
- `helpdesk_custom_renewal_forecast`
- `helpdesk_custom_customer_success_playbook`

Hasil yang diharapkan:

- service review konsisten
- renewal risk terlihat lebih awal
- task customer success terjadwal

### Scenario G: External Integration via API

Use case:

- Sistem eksternal membuat/update ticket dan mengambil KPI.

Endpoint inti:

- `GET /api/helpdesk/v1/health`
- `GET /api/helpdesk/v1/meta`
- `GET /api/helpdesk/v1/tickets`
- `POST /api/helpdesk/v1/tickets/create`
- `POST /api/helpdesk/v1/tickets/<id>/reply`
- `POST /api/helpdesk/v1/tickets/<id>/close`
- `GET /api/helpdesk/v1/kpi/summary`

Contoh urutan integrasi:

1. Validate token dengan `health`.
2. Ambil master IDs (`team`, `category`, `type`) via `meta`.
3. Create ticket dengan payload lengkap.
4. Post reply/update.
5. Close ticket jika validasi stage terpenuhi.
6. Consume KPI summary untuk dashboard eksternal.

Catatan penting environment ini:

- pada mode multi-db local, session perlu terikat ke DB target dulu (`/web?db=ksv17-dev`) agar route custom terbaca konsisten.

Modul yang terlibat:

- `helpdesk_custom_api`
- `helpdesk_custom_customer_communication_log`

## 6. SOP Harian per Peran (Ringkas)

Support Agent:

1. Buka `Tickets` dan filter `Open`, `SLA Watchlist`, `Unassigned`.
2. Pastikan ticket punya `category`, `type`, `assignee`, `priority`.
3. Update customer via channel resmi, cek communication log.
4. Escalate/approval/dispatch jika diperlukan.
5. Close ticket sesuai policy.

Support Lead:

1. Pantau `KPI Overview`, `Communication Analytics`, `Dispatch Board`.
2. Review overdue, escalated, backlog, approval pending.
3. Validasi problem record untuk issue berulang.

Customer Success / Account Manager:

1. Cek `Customer Support Overview`.
2. Review renewals dan renewal forecast.
3. Jalankan playbook dan service review distribution.

## 7. Monitoring and Quality Checks

Functional smoke:

- `docker exec -i odoo17-docker-community-web-1 python3 /mnt/extra-addons/docs/scripts/helpdesk_functional_smoke_test.py --db ksv17-dev --api-token ksv17-demo-api-token`

Daily runner:

- `bash /Users/taufikhidayat/Documents/Projects/Odoo/odoo17-docker-community/addons/docs/scripts/run_helpdesk_smoke_daily.sh`

Automated API tests:

- `docker exec -i odoo17-docker-community-web-1 /usr/bin/odoo -c /etc/odoo/odoo.conf --http-port=8071 -d ksv17-dev -u helpdesk_custom_api --test-enable --test-tags /helpdesk_custom_api --stop-after-init`

## 8. Troubleshooting Cepat

API `404` di local:

- pastikan akses awal ke `/web?db=ksv17-dev` sudah dilakukan dalam session test.

API close gagal dengan validasi:

- pastikan field wajib stage close terisi, biasanya `category`, `type`, `contact`.

Mail queue `exception`:

- set sender config (`mail.default.from` dan domain terkait) agar email notification tidak gagal.

PDF warning `wkhtmltopdf ContentNotFoundError`:

- sering non-blocking di local, tapi tetap perlu hardening asset URL dan mail/report config untuk production.

## 9. Referensi Dokumen Terkait

- `helpdesk_customization_recap.md`
- `helpdesk_pending_backlog.md`
- `README.md` (folder `addons/docs`)

## 10. Cara Pakai Ringkas per Modul Custom

`helpdesk_custom_escalation`:

- atur rule di `Configuration > Escalation Rules`, lalu monitor hasilnya dari ticket smart button `Escalations`.

`helpdesk_custom_kpi`:

- gunakan `Reporting > KPI Overview` untuk monitoring harian dan `KPI Analysis` untuk breakdown mendalam.

`helpdesk_custom_portal`:

- gunakan `Open Public Portal`, `Copy Public Link`, `Send via Email`, `Send via WhatsApp`, dan `Refresh Public Link` dari ticket backend; customer bisa tracking, reply, feedback, close/reopen, escalation request, dan atur notification preference.
- pantau CSAT guardrail di ticket (`Resolution Summary`, low-CSAT recovery, last customer update vs last support update) untuk menjaga kualitas follow-up.

`helpdesk_custom_whatsapp`:

- siapkan template di `Configuration > WhatsApp Templates`, lalu pantau antrian di `Reporting > WhatsApp Logs`.

`helpdesk_custom_invoice`:

- isi timesheet di ticket, lalu jalankan wizard invoice dari ticket untuk billing effort support.

`helpdesk_custom_api`:

- konsumsi endpoint `v1` dengan bearer token untuk create/reply/close ticket dan ambil KPI summary.

`helpdesk_custom_sales_handoff`:

- kirim peluang komersial dari ticket via `Request Sales Follow-up`, review dan convert di menu `Sales Handoffs`.

`helpdesk_custom_approval`:

- ajukan request approval dari ticket, proses approval lifecycle di `Approval Requests`.

`helpdesk_custom_knowledge` dan `helpdesk_custom_knowledge_portal`:

- buat article dari ticket, lanjutkan workflow publish internal/portal, lalu ukur helpful feedback.

`helpdesk_custom_contract` dan `helpdesk_custom_asset_coverage`:

- map kontrak dan asset coverage agar ticket otomatis tahu status entitlement.

`helpdesk_custom_dispatch`, `helpdesk_custom_dispatch_execution`, `helpdesk_custom_field_service_report`:

- jadwalkan onsite, isi checklist eksekusi + evidence, dan tutup loop dengan service report acknowledgement.

`helpdesk_custom_problem_management` dan `helpdesk_custom_release_note_tracking`:

- kelola recurring issue sebagai problem, lalu track release note dan komunikasi fix.

`helpdesk_custom_customer_communication_log` dan `helpdesk_custom_communication_analytics`:

- catat interaksi lintas channel dan analisa response/inactivity untuk kontrol SLA komunikasi.

`helpdesk_custom_customer_360`:

- gunakan `Customer Support Overview` untuk ringkasan kondisi support per customer dalam satu layar.

`helpdesk_custom_contract_renewal`, `helpdesk_custom_contract_renewal_analytics`, `helpdesk_custom_renewal_forecast`:

- monitor renewal watchlist, revenue at risk, dan gap forecast vs target.

`helpdesk_custom_customer_success_playbook`:

- buat playbook proactive per customer/contract, sistem generate activity follow-up otomatis.

`helpdesk_custom_service_review_pack` dan `helpdesk_custom_service_review_distribution`:

- generate pack review customer dan jadwalkan distribusi rutin via email.
