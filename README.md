# Mayz

Mayz adalah website POC untuk membantu proses pelaporan publikasi Instagram Kanwil DJPb. Aplikasi ini dibuat agar user non-IT bisa upload template, mengatur scraping, menjalankan proses, melihat hasil, dan download Excel tanpa perlu membuka script Python.

## Fitur

- Upload template Excel dengan drag and drop
- Membaca daftar akun dari sheet `DJPB`
- Visual flow seperti pipeline proses
- Form konfigurasi scraping
- Public scraping Instagram tanpa API, tanpa login, tanpa proxy
- Ambil link postingan, tanggal, caption, jenis media, like, comment, dan total engagement jika terbaca
- Export laporan Excel sesuai format pelaporan
- Preview hasil di website
- Template kosong untuk uji coba

## Struktur Folder

```text
mayz/
├── app.py
├── requirements.txt
├── README.md
├── assets/
│   └── logo/
│       └── mayz.png
├── data/
│   └── template_mayz_djpb.xlsx
├── exports/
├── src/
│   ├── config.py
│   ├── excel_builder.py
│   ├── parser.py
│   ├── scraper.py
│   └── ui.py
└── static/
    └── style.css
```

## Cara Install

Masuk ke folder project:

```powershell
cd mayz
```

Install library:

```powershell
python -m pip install -r requirements.txt
```

Install browser Playwright:

```powershell
python -m playwright install chromium
```

## Cara Menjalankan

```powershell
streamlit run app.py
```

Setelah itu browser akan membuka halaman aplikasi Mayz.

## Cara Menggunakan

1. Download template kosong dari aplikasi.
2. Isi sheet `DJPB`.
3. Pastikan kolom B berisi nama Kanwil, misalnya `Kanwil DJPb Provinsi Aceh`.
4. Pastikan kolom C berisi URL Instagram, misalnya `https://www.instagram.com/djpbaceh/`.
5. Upload file template ke aplikasi.
6. Atur periode laporan, jumlah postingan, jumlah scroll, dan delay.
7. Pilih data tambahan yang ingin dimasukkan ke output.
8. Klik `Mulai scraping`.
9. Tunggu proses selesai.
10. Download file Excel hasil pelaporan.

## Format Template

Sheet yang wajib ada:

```text
DJPB
```

Header utama:

```text
No.
Nama Kanwil
Nama Unit Eselon III
Tanggal Postingan
Jenis Kegiatan
Judul Postingan
Link
Jenis Media Sosial
Jumlah Reach / Audiens
No. Agenda Setting
Topik Agenda Setting
```

## Batasan POC

Mayz pada tahap ini menggunakan public scraping. Aplikasi tidak menggunakan API resmi Meta, tidak melakukan login, tidak menggunakan proxy, dan tidak melakukan bypass. Data seperti reach atau audiens tidak diambil karena bukan data publik. Like dan komentar hanya akan terisi jika tersedia pada metadata publik halaman Instagram.

Jika Instagram mengubah struktur halaman, menampilkan login wall, atau membatasi akses publik, hasil scraping bisa berubah atau tidak lengkap. Untuk implementasi production yang lebih stabil, opsi yang lebih aman adalah Instagram Graph API resmi atau tools monitoring yang disetujui.

## Troubleshooting

Jika Playwright belum terinstall:

```powershell
python -m playwright install chromium
```

Jika aplikasi tidak menemukan akun:

- Pastikan file yang diupload adalah `.xlsx`
- Pastikan sheet bernama `DJPB`
- Pastikan kolom B berisi nama Kanwil
- Pastikan kolom C berisi URL Instagram
- Pastikan nama Kanwil diawali `Kanwil DJPb`

Jika scraping lama:

- Kurangi maksimal postingan per akun
- Kurangi jumlah scroll
- Nonaktifkan ambil detail postingan
- Naikkan delay jika sering gagal

Jika like/comment kosong:

- Metadata publik Instagram kemungkinan tidak menampilkan data tersebut
- Data ini tetap bisa direview manual atau menggunakan API/tools resmi pada tahap lanjutan