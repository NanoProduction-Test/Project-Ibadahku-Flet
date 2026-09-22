# IbadahKu

Aplikasi pendamping ibadah sederhana berbasis Kivy untuk desktop/Windows.

## Fitur
- Jadwal sholat berdasarkan kota atau lokasi otomatis.
- Pengingat waktu sholat dan kegiatan saat aplikasi terbuka.
- Ceklis ibadah harian + streak.
- Progress ibadah harian.
- Timer sesi ibadah/belajar.
- Tasbih digital dengan target 33, 99, 100, 1000, atau bebas.
- Statistik aktivitas hari ini, 7 hari terakhir, dan total.
- Koleksi 25+ doa pendek, navigasi acak, dan favorit yang tersimpan di SQLite.
- Arah kiblat berdasarkan koordinat kota/lokasi.
- Mode gelap yang berubah langsung.
- Database SQLite lokal.

## Menjalankan di Windows
Dari folder yang berisi `main.py`:

```powershell
python main.py
```

## Instalasi dependency
```powershell
python -m pip install -r requirements.txt
```

## Catatan
Fitur alarm/notifikasi bekerja ketika aplikasi sedang terbuka. Jadwal sholat membutuhkan koneksi internet saat data belum tersedia di cache.
