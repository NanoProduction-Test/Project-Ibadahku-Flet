🕌 IbadahKu
Pendamping ibadah harianmu — jadwal sholat otomatis, checklist ibadah, tasbih digital, doa harian, dan arah kiblat dalam satu aplikasi.

Dibuat dengan Python + Flet · Tersedia untuk Android (APK) dan Desktop

✨ Fitur
📅 Jadwal sholat otomatis — sesuai kota pilihanmu (metode resmi Kemenag RI), lengkap dengan hitungan mundur real-time
☑️ Checklist ibadah harian — tandai sholat & amalanmu, jaga streak harianmu
📋 Kegiatan pribadi — catat rutinitas: ngaji, belajar, olahraga (tambah, edit, hapus)
⏱️ Timer fokus ibadah — untuk tilawah, hafalan, atau dzikir tanpa distraksi
📿 Tasbih digital — cincin 33 butir menyala mengelilingi hitungan, ganti dzikir & target sesukamu
📖 Doa harian — 24 doa pilihan: teks Arab, latin, arti, pencarian, dan favorit
🧭 Arah kiblat — arah Ka'bah dari kotamu, lengkap dengan kompas
📊 Statistik 7 hari & pencapaian — pantau konsistensimu, buka lencana 🏆
🌙 Mode gelap + 5 pilihan warna tema
📱 Cara Memasang di HP
Download file ibadahku.apk
Buka file tersebut di HP (biasanya di folder Download)
Muncul peringatan "sumber tidak dikenal"? → Settings → Izinkan (normal, karena bukan dari Play Store)
Tekan Install → selesai 🎉
💡 Internet hanya dibutuhkan saat pertama kali mengambil jadwal sholat setiap hari. Setelah terunduh, jadwal tetap bisa dilihat offline.

🚀 Panduan Pemakaian Singkat
Pertama kali (2 menit):

Buka tab Atur → pilih kotamu → jadwal sholat otomatis menyesuaikan
Selesai!
Sehari-hari:

Tab	Fungsinya
Beranda	Jadwal sholat + ayat hari ini + checklist ibadah — centang tiap selesai
Kegiatan	Rutinitasmu: tekan + Tambah untuk baru, ketuk kartu untuk edit
Fokus	Pilih durasi → Mulai → beribadah khusyuk
Tasbih	Tap tombol besar (atau cincinnya) tiap dzikir
Atur	Kota, tema, doa harian, kiblat, statistik, pencapaian
❓ FAQ
Kenapa jadwal sholatnya tidak muncul?Pastikan internet aktif saat pertama kali membuka aplikasi di hari itu. Setelah terunduh, tersimpan untuk offline.

Apakah data hilang kalau aplikasi ditutup?Tidak. Checklist, kegiatan, hitungan tasbih, dan pengaturan tersimpan permanen di perangkat.

Jadwalnya akurat?Ya — dihitung dengan metode resmi Kementerian Agama RI (via layanan AlAdhan) sesuai koordinat kotamu.

Gratis? Ada iklan?100% gratis, tanpa iklan, tanpa akun, tanpa pelacakan. Data kamu tidak dikirim ke mana pun.

👨‍💻 Untuk Pengembang
Ingin menjalankan dari kode sumber?

pip install -r requirements.txtpython main.py --web
Struktur kode:

File	Peran
main.py	Antarmuka & logika aplikasi (Flet)
database.py	Penyimpanan data (SQLite)
prayertimes.py	API AlAdhan + perhitungan kiblat
doa.py	Koleksi doa harian
achievements.py	Sistem pencapaian
Build APK sendiri: flet build apk (butuh Flutter SDK + Android SDK)

📖 Riwayat Proyek
Dikembangkan bertahap selama ±4 minggu: awalnya dibangun dengan Kivy, kemudian dimigrasi total ke Flet demi tampilan modern yang responsif di layar HP. Riwayat lengkapnya ada di tab Commits.