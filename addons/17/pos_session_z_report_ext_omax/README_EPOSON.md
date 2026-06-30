# POS Session Z Report dengan Epson Printer Integration

## Deskripsi
Addon ini telah di-upgrade untuk mendukung **direct printing ke Epson thermal printer** tanpa perlu IoT Box. Sekarang tombol "Session Report" bisa langsung mencetak ke Epson printer atau generate PDF report.

## Fitur Baru

### 1. Epson Direct Printing
- **Direct connection** ke Epson thermal printer via IP address
- **Menggunakan konfigurasi yang sudah ada** di point_of_sale inti
- **No IoT Box required** - lebih cost effective
- **Data format identik** dengan yang dikirim ke IoT Box

### 2. Print Method Selection
Ketika klik tombol "Session Report", user akan mendapat pilihan:
- **Print to Epson Thermal Printer** - Direct print ke thermal printer (jika ePos printer diaktifkan)
- **Generate PDF Report** - Original functionality (generate PDF)

### 3. Konfigurasi yang Digunakan
**TIDAK perlu konfigurasi tambahan!** Addon ini menggunakan field yang sudah ada di point_of_sale inti:

- **`other_devices`** (boolean): Checkbox "ePos Printer" di POS settings
- **`epos_printer_ip`** (char): Field IP address printer ePos

### 4. Cara Konfigurasi
1. Buka **POS Configuration** → **Settings**
2. Aktifkan checkbox **"ePos Printer"** (Connect device to your PoS without an IoT Box)
3. Masukkan **IP Address** printer ePos (default: 192.168.0.250)
4. Save konfigurasi

## Teknologi

### 1. Arsitektur Printer
- **Extends BasePrinter** dari point_of_sale
- **Override sendPrintingJob()** seperti HWPrinter
- **Menggunakan endpoint yang sama**: `/hw_proxy/default_printer_action`
- **Data format identik**: JPEG base64 string

### 2. Flow Printing
```
HTML Receipt → Canvas → JPEG Base64 → Epson Printer
     ↓              ↓         ↓           ↓
  Session      htmlToCanvas  processCanvas  /hw_proxy/default_printer_action
  Data         (point_of_sale) (point_of_sale)  (endpoint yang sama)
```

### 3. Fallback System
Jika direct connection ke Epson printer gagal:
- **Browser Print Fallback** menggunakan `window.print()`
- **Format thermal printer** (80mm width)
- **Image quality optimal** untuk thermal printing

## Instalasi

### 1. Install Addon
```bash
# Addon sudah include di manifest
# Tidak perlu konfigurasi tambahan
```

### 2. Konfigurasi POS
- Buka **Point of Sale** → **Configuration** → **Settings**
- Aktifkan **"ePos Printer"**
- Masukkan **IP Address** printer
- Save dan restart POS

### 3. Test Printing
- Buka POS session
- Klik tombol **"Session Report"**
- Pilih **"Print to Epson Thermal Printer"**
- Receipt akan langsung tercetak di thermal printer

## Dependencies

- **point_of_sale** (Odoo core module) - **WAJIB**
- **Tidak ada dependency tambahan**

## Kompatibilitas

- **Odoo 18.0+**
- **Epson thermal printer** dengan network support
- **Printer IP** harus accessible dari Odoo server

## Keuntungan

### 1. **Cost Effective**
- Tidak perlu IoT Box
- Langsung connect ke printer via network
- Hardware investment minimal

### 2. **Easy Setup**
- Konfigurasi sudah ada di point_of_sale
- Tidak perlu field tambahan
- UI yang familiar

### 3. **100% Compatible**
- Data format identik dengan IoT Box
- Endpoint yang sama
- Arsitektur yang konsisten

### 4. **Robust Fallback**
- Multiple connection methods
- Browser print fallback
- Error handling yang baik

## Troubleshooting

### 1. Printer Tidak Terdeteksi
- Check IP address printer
- Pastikan printer online dan accessible
- Test ping dari Odoo server

### 2. Print Gagal
- Check network connectivity
- Pastikan port 9100 terbuka
- Gunakan browser print fallback

### 3. Format Tidak Sesuai
- Pastikan printer support thermal format
- Check printer settings (80mm width)
- Test dengan browser print dulu

## Author
Custom Development - Menggunakan arsitektur point_of_sale inti

## License
GPL-3.0 - Sesuai dengan point_of_sale core module
