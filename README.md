IbadahKu (Flet)
Pendamping ibadah harian: jadwal sholat otomatis, checklist ibadah, timerfokus, tasbih digital, doa harian, arah kiblat, statistik, dan pencapaian.Versi ini adalah hasil migrasi dari versi Kivy keFlet, dengan tampilan dirombak total ke gaya"Zamrud & Emas" yang responsif di layar HP.

## ✨ Fitur

### 🏠 Beranda
- Jadwal sholat hari ini dengan **countdown real-time**
- Ayat pilihan harian
- Checklist ibadah dengan **streak**

### ✅ Kegiatan
- Tambah rutinitas pribadi
- Edit dan hapus kegiatan
- Tandai kegiatan sebagai selesai

### ⏱️ Fokus
- Timer sesi ibadah ala **Pomodoro**
- Total menit fokus tersimpan

### 📿 Tasbih
- Counter dzikir dengan cincin **33 butir**
- Pilihan dzikir yang dapat diubah
- Target dzikir dapat disesuaikan

### 🤲 Doa Harian
- **24 pilihan doa**
- Teks Arab, latin, dan arti
- Pencarian doa
- Fitur favorit

### 🧭 Arah Kiblat
- Sudut kiblat berdasarkan kota yang dipilih
- Kompas

### 📊 Statistik & Pencapaian
- Ringkasan aktivitas **7 hari**
- Lencana dan pencapaian

### ⚙️ Atur
- Pilih kota
- Mode gelap
- **5 pilihan warna aksen**

## 🌐 Data & Penyimpanan

- Jadwal sholat diambil dari **API AlAdhan** menggunakan metode **Kemenag RI**.
- Data jadwal di-cache ke **SQLite**, sehingga tetap dapat dilihat saat offline.
- Seluruh data aplikasi disimpan secara lokal di perangkat menggunakan **SQLite**.

## 🛠️ Menjalankan (Mode Pengembangan)

### 1. Buat virtual environment

```bash
python -m venv .venv
```

### 2. Aktifkan virtual environment

**Windows:**

```powershell
.venv\Scripts\activate
```

### 3. Install dependency

```bash
pip install -r requirements.txt
```

### 4. Jalankan aplikasi

**Mode web:**

```bash
python main.py --web
```

Mode ini dapat digunakan untuk menguji tampilan HP melalui browser. Buka dari HP yang terhubung ke **Wi-Fi yang sama**.

**Mode desktop:**

```bash
python main.py
```

## 📱 Build APK Android

Untuk membuat APK Android:

```bash
flet build apk
```

Flet membutuhkan **Flutter SDK** dan **Android SDK**. Saat pertama kali digunakan, Flet dapat menawarkan instalasi otomatis untuk komponen yang diperlukan.

Hasil build tersedia di:

```text
build/apk/
```

## 📁 Struktur Proyek

```text
.
├── main.py
├── database.py
├── prayertimes.py
├── doa.py
├── achievements.py
├── pyproject.toml
└── assets/
    └── fonts/
        └── # font Arab (NotoNaskh)
```

### Penjelasan file

| File / Folder | Fungsi |
|---|---|
| `main.py` | Seluruh UI dan logika aplikasi (5 halaman + dialog) |
| `database.py` | SQLite untuk kegiatan, checklist, tasbih, dan statistik |
| `prayertimes.py` | API AlAdhan dan perhitungan arah kiblat |
| `doa.py` | Koleksi doa harian |
| `achievements.py` | Sistem lencana dan pencapaian |
| `pyproject.toml` | Identitas aplikasi untuk build Android |
| `assets/fonts/` | Font Arab, termasuk NotoNaskh |

## 🔄 Catatan Migrasi Kivy → Flet

Proyek awalnya dibangun dengan **Kivy** selama 4 minggu. Setelah itu, aplikasi dimigrasikan total ke **Flet 1.0**.

Beberapa catatan penting dari proses migrasi:

- Event `Dropdown` di Flet 1.0 menggunakan `on_select`, bukan `on_change`.
- `Row` menggunakan `vertical_alignment`, sedangkan `Column` menggunakan `horizontal_alignment`.
- Dialog dibuka menggunakan `page.show_dialog()` dan ditutup dengan `page.pop_dialog()`.
- Database harus ditempatkan pada lokasi yang benar-benar dapat ditulis. Pada Android, lokasi penyimpanan diuji menggunakan beberapa kandidat sampai ditemukan lokasi yang writable.
- Timer dan countdown menggunakan task async (`asyncio`), bukan thread, agar UI tidak membeku.

## 📜 Riwayat Pengembangan

IbadahKu dikembangkan sebagai **project belajar Python**.

Selama sekitar 4 minggu, versi Kivy dikembangkan dengan fitur utama berupa:

- timeline/jadwal sholat
- kegiatan
- timer
- tasbih
- doa
- kiblat

Setelah itu, proyek dipindahkan total ke Flet untuk mendapatkan tampilan dan target platform **web, desktop, dan Android** yang lebih modern.

**Build APK telah diuji langsung pada perangkat Android.**
Hasil build ada di folder build\apk\.
