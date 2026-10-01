IbadahKu (Flet)
Pendamping ibadah harian: jadwal sholat otomatis, checklist ibadah, timerfokus, tasbih digital, doa harian, arah kiblat, statistik, dan pencapaian.Versi ini adalah hasil migrasi dari versi Kivy keFlet, dengan tampilan dirombak total ke gaya"Zamrud & Emas" yang responsif di layar HP.

Fitur
Beranda — jadwal sholat hari ini dengan countdown real-time,ayat pilihan harian, checklist ibadah dengan streak
Kegiatan — rutinitas pribadi: tambah, edit, hapus, tandai selesai
Fokus — timer sesi ibadah ala pomodoro, total menit tersimpan
Tasbih — counter dzikir dengan cincin 33 butir, pilihan dzikirdan target yang bisa diubah
Doa Harian — 24 doa dengan teks Arab, latin, arti; pencariandan favorit
Arah Kiblat — sudut kiblat dari kota terpilih + kompas
Statistik & Pencapaian — ringkasan 7 hari dan lencana
Atur — pilih kota, mode gelap, 5 warna aksen
Jadwal sholat diambil dari API AlAdhan (metode Kemenag RI), laludi-cache ke SQLite sehingga tetap bisa dilihat offline
Semua data tersimpan lokal di perangkat (SQLite)
Menjalankan (mode pengembangan)
python -m venv .venv.venv\Scripts\activate      # Windowspip install -r requirements.txtpython main.py --web        # via browser (tes tampilan HP: buka dari HP, satu WiFi)python main.py              # atau mode jendela desktop
Build APK Android
flet build apk
Butuh Flutter SDK dan Android SDK (flet akan menawarkan instalasiotomatis saat pertama kali). Hasil build ada di folder build\apk\.

Struktur Proyek
main.py                     # seluruh UI & logika (5 halaman + dialog)database.py                 # SQLite: kegiatan, ceklis, tasbih, statistikprayertimes.py              # API AlAdhan + perhitungan arah kiblatdoa.py                      # koleksi doa harianachievements.py             # sistem lencana/pencapaianpyproject.toml              # identitas app untuk build Androidassets/fonts/               # font Arab (NotoNaskh)
Catatan Migrasi
Proyek awalnya dibangun dengan Kivy selama 4 minggu (lihat riwayatcommit di bawah), lalu dimigrasi total ke Flet 1.0. Beberapa hal yangperlu diperhatikan kalau mengembangkan lebih lanjut:

Event Dropdown di Flet 1.0 bernama on_select, bukan on_change
Row memakai vertical_alignment, Column memakai horizontal_alignment
Dialog dibuka dengan page.show_dialog() dan ditutup denganpage.pop_dialog()
Database harus diletakkan di lokasi yang benar-benar writable:di Android, folder home menunjuk ke /data yang terkunci sistem,jadi lokasi penyimpanan dipilih dengan uji-tulis beberapa kandidat
Timer dan countdown memakai task async (asyncio), bukan thread,agar UI tidak membeku
Riwayat
Dikembangkan sebagai project belajar Python: 4 minggu dengan Kivy(timeline sholat, kegiatan, timer, tasbih, doa, kiblat), lalu pindahtotal ke Flet untuk tampilan web/desktop/Android yang lebih modern.Build APK diuji langsung di perangkat Android.