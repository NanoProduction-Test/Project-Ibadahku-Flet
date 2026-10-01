IbadahKu (Flet)
Pendamping ibadah harian: jadwal sholat otomatis, checklist ibadah, timer fokus, tasbih digital, doa harian, arah kiblat, statistik, dan pencapaian. Versi ini adalah hasil migrasi dari Kivy ke Flet, dengan tampilan dirombak total ke gaya "Zamrud & Emas" yang responsif di layar HP.

Fitur
Beranda — jadwal sholat hari ini dengan countdown real-time, ayat pilihan harian, checklist ibadah dengan streak
Kegiatan — rutinitas pribadi: tambah, edit, hapus, tandai selesai
Fokus — timer sesi ibadah ala pomodoro, total menit per hari tersimpan
Tasbih — counter dzikir dengan cincin 33 butir, dzikir dan target bisa diganti
Doa Harian — 24 doa pilihan: teks Arab, latin, arti, pencarian, dan favorit
Arah Kiblat — sudut kiblat dari kota terpilih, lengkap dengan kompas
Statistik dan Pencapaian — ringkasan 7 hari dan lencana
Atur — pilih kota, mode gelap, 5 warna aksen
Jadwal sholat diambil dari API AlAdhan (metode Kemenag RI), lalu di-cache ke SQLite sehingga tetap bisa dibaca offline
Semua data tersimpan lokal di perangkat
Menjalankan
Install Python 3.10 atau lebih baru
Install dependensi: jalankan perintah pip install -r requirements.txt
Jalankan aplikasi: python main.py --web (mode browser) atau python main.py (jendela desktop)
Build APK Android
Jalankan perintah flet build apk — butuh Flutter SDK dan Android SDK, dan flet akan menawarkan instalasi otomatis saat pertama kali. Hasil build ada di folder build/apk.

Struktur Proyek
main.py — seluruh UI dan logika aplikasi (5 halaman + dialog)
database.py — penyimpanan SQLite: kegiatan, ceklis, tasbih, statistik
prayertimes.py — API AlAdhan dan perhitungan arah kiblat
doa.py — koleksi doa harian
achievements.py — sistem lencana pencapaian
pyproject.toml — identitas aplikasi untuk build Android
assets/fonts — font Arab (NotoNaskh)