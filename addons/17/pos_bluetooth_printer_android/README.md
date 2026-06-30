# POS Bluetooth Printer Android

Addon ini menambahkan cetak struk POS langsung ke printer thermal Bluetooth dari browser Chrome di Android.

Target utama:
- Tablet Android
- Printer Panda PRJ-R58B-II
- Mode koneksi Bluetooth classic yang muncul sebagai serial port

Cara pakai:
1. Install addon ini.
2. Aktifkan `Bluetooth Receipt Printer` di setting POS.
3. Pair printer Panda di Android Settings.
4. Buka POS pakai Chrome.
5. Di halaman receipt, tap `Connect Bluetooth Printer` saat pertama kali.
6. Setelah izin serial diberikan, tombol `Print Receipt` akan kirim struk langsung ke printer.

Catatan:
- Fitur ini memakai Web Serial API, bukan IoT Box.
- Browser yang paling aman untuk skenario ini adalah Google Chrome Android.
- Untuk auto print, printer harus pernah diotorisasi dulu dari browser yang sama.
