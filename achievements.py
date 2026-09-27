"""Sistem pencapaian (achievement/badge) IbadahKu."""

import database as db
from datetime import date

DAFTAR_BADGE = [
    {"id": "streak_3", "emoji": "🔥", "judul": "Semangat Baru",
     "deskripsi": "Streak ceklis 3 hari berturut-turut"},
    {"id": "streak_7", "emoji": "⭐", "judul": "Konsisten Sepekan",
     "deskripsi": "Streak ceklis 7 hari berturut-turut"},
    {"id": "streak_30", "emoji": "🏆", "judul": "Istiqomah Sebulan",
     "deskripsi": "Streak ceklis 30 hari berturut-turut"},
    {"id": "tasbih_100", "emoji": "📿", "judul": "Penjaga Lisan",
     "deskripsi": "Total tasbih mencapai 100 kali"},
    {"id": "tasbih_1000", "emoji": "💎", "judul": "Ahli Dzikir",
     "deskripsi": "Total tasbih mencapai 1.000 kali"},
    {"id": "tasbih_10000", "emoji": "👑", "judul": "Muadzin Hati",
     "deskripsi": "Total tasbih mencapai 10.000 kali"},
    {"id": "timer_60", "emoji": "⏱️", "judul": "Satu Jam Fokus",
     "deskripsi": "Total timer ibadah mencapai 60 menit"},
    {"id": "timer_300", "emoji": "🕐", "judul": "Lima Jam Ibadah",
     "deskripsi": "Total timer ibadah mencapai 300 menit"},
    {"id": "timer_1000", "emoji": "🌟", "judul": "Pejuang Waktu",
     "deskripsi": "Total timer ibadah mencapai 1.000 menit"},
    {"id": "pertama", "emoji": "🌱", "judul": "Langkah Pertama",
     "deskripsi": "Menyelesaikan ceklis pertama kali"},
]


def evaluasi():
    """Cek semua badge, unlock yang belum tercapai. Return list badge baru."""
    sudah = db.ambil_achievement()
    streak = db.hitung_streak()
    total_menit, total_tasbih = db.total_keseluruhan()
    hari_ini = date.today().isoformat()
    status = db.status_ceklis(hari_ini)
    ada_selesai = any(v for v in status.values())

    kondisi = {
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
        "streak_30": streak >= 30,
        "tasbih_100": total_tasbih >= 100,
        "tasbih_1000": total_tasbih >= 1000,
        "tasbih_10000": total_tasbih >= 10000,
        "timer_60": total_menit >= 60,
        "timer_300": total_menit >= 300,
        "timer_1000": total_menit >= 1000,
        "pertama": ada_selesai,
    }

    baru = []
    for badge in DAFTAR_BADGE:
        bid = badge["id"]
        if bid not in sudah and kondisi.get(bid, False):
            db.simpan_achievement(bid, hari_ini)
            baru.append(badge)
    return baru


def semua_dengan_status():
    """Return semua badge beserta status unlock."""
    sudah = db.ambil_achievement()
    hasil = []
    for b in DAFTAR_BADGE:
        hasil.append({
            **b,
            "tercapai": b["id"] in sudah,
            "tanggal": sudah.get(b["id"], ""),
        })
    return hasil
