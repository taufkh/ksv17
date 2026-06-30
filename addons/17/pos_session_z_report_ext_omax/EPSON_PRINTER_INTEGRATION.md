# Integrasi Printer Epson untuk POS Session Z Report

## Deskripsi
Modul ini telah diintegrasikan dengan printer Epson untuk mencetak Session Z Report langsung ke printer thermal tanpa perlu generate PDF terlebih dahulu.

## Fitur
- ✅ Print langsung ke printer Epson thermal
- ✅ Menggunakan endpoint Epson ePOS yang sama dengan addon `pos_epson_printer`
- ✅ Fallback ke PDF jika printer Epson tidak tersedia
- ✅ Support untuk semua model printer Epson yang kompatibel dengan ePOS

## Konfigurasi

### 1. Konfigurasi Printer Epson
Pastikan addon `pos_epson_printer` sudah terinstall dan dikonfigurasi:

1. Buka **Point of Sale > Configuration > Point of Sale**
2. Pilih POS yang akan dikonfigurasi
3. Di bagian **Other Devices**, masukkan IP Address printer Epson
4. Pastikan field `Epson Receipt Printer IP Address` terisi

### 2. Konfigurasi Session Z Report
1. Di POS Configuration yang sama, aktifkan **Session Z Report**
2. Pilih opsi detail yang ingin ditampilkan dalam report

## Cara Kerja

### Flow Print Session Report:
1. User klik tombol **Session Report** di POS
2. Sistem mengecek apakah printer Epson tersedia
3. Jika tersedia:
   - Ambil data session dari database
   - Generate canvas dengan data session
   - Convert canvas ke raster image
   - Kirim ke printer Epson via ePOS endpoint
4. Jika tidak tersedia atau error:
   - Fallback ke PDF generation (seperti sebelumnya)

### Endpoint Epson:
```
http://[PRINTER_IP]/cgi-bin/epos/service.cgi?devid=local_printer
```

## Struktur File

```
pos_session_z_report_ext_omax/
├── static/src/app/pos_session_report/
│   ├── pos_session_report.js          # Main control buttons logic
│   ├── pos_session_report.xml         # UI template
│   └── epson_printer_service.js       # Epson printer service
├── __manifest__.py                    # Module manifest
└── EPSON_PRINTER_INTEGRATION.md       # Dokumentasi ini
```

## Dependencies
- `point_of_sale` - Core POS functionality
- `pos_epson_printer` - Epson printer support

## Troubleshooting

### Printer tidak terdeteksi:
1. Pastikan IP address printer benar
2. Cek koneksi network ke printer
3. Pastikan printer support ePOS protocol

### Print gagal:
1. Cek status printer (paper, error codes)
2. Cek log browser console untuk error details
3. Pastikan printer tidak sedang busy

### Fallback ke PDF:
- Jika ada error dengan printer Epson, sistem akan otomatis generate PDF
- Cek log untuk detail error yang terjadi

## Error Codes Epson
- `DeviceNotFound`: Periksa konfigurasi Device ID
- `EPTR_REC_EMPTY`: Tidak ada kertas di printer
- `EPTR_COVER_OPEN`: Cover printer terbuka

## Support
Untuk bantuan teknis, silakan hubungi tim development atau buat issue di repository.
