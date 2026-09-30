import os
import sqlite3
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Database harus berada di lokasi writable agar build Android dapat menyimpan
# checklist, tasbih, timer, favorit, dan pengaturan.
DATA_DIR = os.path.join(os.path.expanduser("~"), "IbadahKu")
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, "ibadahku.db")
BUNDLED_DB = os.path.join(BASE_DIR, "ibadahku.db")

# Saat pertama kali pindah dari versi desktop, salin database lama jika ada.
if not os.path.exists(DB) and os.path.exists(BUNDLED_DB):
    try:
        import shutil
        shutil.copy2(BUNDLED_DB, DB)
    except OSError:
        pass

NAMA_WAKTU = ["Subuh", "Dzuhur", "Ashar", "Maghrib", "Isya"]

CEKLIS_DEFAULT = [
    "Sholat Subuh", "Sholat Dzuhur", "Sholat Ashar",
    "Sholat Maghrib", "Sholat Isya",
    "Tilawah Qur'an", "Dzikir pagi", "Dzikir petang",
]


def buat_tabel():
    with sqlite3.connect(DB) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS kegiatan (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nama     TEXT NOT NULL,
                jam      TEXT NOT NULL,
                hari     TEXT NOT NULL DEFAULT 'Setiap hari',
                kategori TEXT NOT NULL DEFAULT 'Ibadah',
                aktif    INTEGER NOT NULL DEFAULT 1
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS pengaturan (
                kunci TEXT PRIMARY KEY,
                nilai TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS jadwal_cache (
                kota    TEXT NOT NULL,
                tanggal TEXT NOT NULL,
                subuh TEXT, dzuhur TEXT, ashar TEXT,
                maghrib TEXT, isya TEXT,
                PRIMARY KEY (kota, tanggal)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS ceklis (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                aktif INTEGER NOT NULL DEFAULT 1
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS ceklis_log (
                tanggal TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                selesai INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tanggal, item_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS kegiatan_log (
                tanggal TEXT NOT NULL,
                kegiatan_id INTEGER NOT NULL,
                selesai INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tanggal, kegiatan_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS timer_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT NOT NULL,
                menit   INTEGER NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS tasbih_log (
                tanggal  TEXT PRIMARY KEY,
                hitungan INTEGER NOT NULL DEFAULT 0
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS doa_favorit (
                nomor INTEGER PRIMARY KEY
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS achievement (
                id TEXT PRIMARY KEY,
                tercapai INTEGER NOT NULL DEFAULT 0,
                tanggal TEXT
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS ayat_cache (
                tanggal TEXT PRIMARY KEY,
                surah TEXT,
                ayat TEXT,
                teks_arab TEXT,
                teks_indo TEXT
            )"""
        )
        if con.execute("SELECT COUNT(*) FROM ceklis").fetchone()[0] == 0:
            for nama in CEKLIS_DEFAULT:
                con.execute("INSERT INTO ceklis (nama) VALUES (?)", (nama,))
        else:
            # Migrasi kecil untuk database lama: versi sebelumnya bisa meninggalkan
            # semua checklist default sebagai nonaktif setelah penghapusan.
            rows = con.execute("SELECT nama, aktif FROM ceklis").fetchall()
            nama_rows = {r[0] for r in rows}
            punya_kustom = bool(nama_rows - set(CEKLIS_DEFAULT))
            if not punya_kustom and rows and not any(r[1] for r in rows):
                con.executemany(
                    "UPDATE ceklis SET aktif = 1 WHERE nama = ?",
                    [(nama,) for nama in CEKLIS_DEFAULT],
                )


# ---------------- kegiatan ----------------

def tambah(nama, jam, hari, kategori):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO kegiatan (nama, jam, hari, kategori) VALUES (?, ?, ?, ?)",
            (nama, jam, hari, kategori),
        )


def semua():
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return con.execute("SELECT * FROM kegiatan ORDER BY jam").fetchall()


def kegiatan_hari_ini(nama_hari):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return con.execute(
            """SELECT * FROM kegiatan
               WHERE aktif = 1 AND (hari = ? OR hari = 'Setiap hari')
               ORDER BY jam""",
            (nama_hari,),
        ).fetchall()


def hapus(id_kegiatan):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM kegiatan WHERE id = ?", (id_kegiatan,))
        con.execute("DELETE FROM kegiatan_log WHERE kegiatan_id = ?", (id_kegiatan,))


def status_kegiatan(tanggal):
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT kegiatan_id, selesai FROM kegiatan_log WHERE tanggal = ?",
            (tanggal,),
        ).fetchall()
    return {r[0]: bool(r[1]) for r in rows}


def set_kegiatan_selesai(kegiatan_id, tanggal, selesai):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO kegiatan_log (tanggal, kegiatan_id, selesai) VALUES (?, ?, ?) "
            "ON CONFLICT(tanggal, kegiatan_id) DO UPDATE SET selesai=excluded.selesai",
            (tanggal, kegiatan_id, 1 if selesai else 0),
        )


# ---------------- pengaturan ----------------

def simpan_pengaturan(kunci, nilai):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES (?, ?)",
            (kunci, nilai),
        )


def ambil_pengaturan(kunci, default=None):
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,)
        ).fetchone()
        return baris[0] if baris else default


# ---------------- cache jadwal sholat ----------------

def simpan_jadwal(kota, tanggal, jadwal):
    jam = [waktu for _, waktu in jadwal]
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT OR REPLACE INTO jadwal_cache VALUES (?,?,?,?,?,?,?)",
            (kota, tanggal, *jam),
        )


def ambil_jadwal(kota, tanggal):
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT subuh, dzuhur, ashar, maghrib, isya FROM jadwal_cache"
            " WHERE kota = ? AND tanggal = ?",
            (kota, tanggal),
        ).fetchone()
    if baris is None:
        return None
    return list(zip(NAMA_WAKTU, baris))


# ---------------- ceklis harian ----------------

def semua_ceklis():
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return con.execute(
            "SELECT * FROM ceklis WHERE aktif = 1 ORDER BY id").fetchall()


def status_ceklis(tanggal):
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT item_id, selesai FROM ceklis_log WHERE tanggal = ?",
            (tanggal,),
        ).fetchall()
    return {b[0]: bool(b[1]) for b in baris}


def toggle_ceklis(item_id, tanggal):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT OR IGNORE INTO ceklis_log (tanggal, item_id, selesai)"
            " VALUES (?, ?, 0)", (tanggal, item_id))
        con.execute(
            "UPDATE ceklis_log SET selesai = 1 - selesai"
            " WHERE tanggal = ? AND item_id = ?", (tanggal, item_id))



def set_ceklis(item_id, tanggal, selesai):
    """Set status ceklis secara eksplisit; tidak bergantung pada toggle UI."""
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO ceklis_log (tanggal, item_id, selesai) VALUES (?, ?, ?) "
            "ON CONFLICT(tanggal, item_id) DO UPDATE SET selesai=excluded.selesai",
            (tanggal, item_id, 1 if selesai else 0),
        )


def set_semua_ceklis(tanggal, selesai):
    with sqlite3.connect(DB) as con:
        ids = [r[0] for r in con.execute("SELECT id FROM ceklis WHERE aktif=1").fetchall()]
        for item_id in ids:
            con.execute(
                "INSERT INTO ceklis_log (tanggal, item_id, selesai) VALUES (?, ?, ?) "
                "ON CONFLICT(tanggal, item_id) DO UPDATE SET selesai=excluded.selesai",
                (tanggal, item_id, 1 if selesai else 0),
            )


def tambah_item_ceklis(nama):
    with sqlite3.connect(DB) as con:
        con.execute("INSERT INTO ceklis (nama) VALUES (?)", (nama,))


def hapus_item_ceklis(item_id):
    with sqlite3.connect(DB) as con:
        con.execute("UPDATE ceklis SET aktif = 0 WHERE id = ?", (item_id,))


def hitung_streak():
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT DISTINCT tanggal FROM ceklis_log WHERE selesai = 1"
            " ORDER BY tanggal DESC").fetchall()
    tanggal_ada = {b[0] for b in baris}
    hari = date.today()
    if hari.isoformat() not in tanggal_ada:
        hari -= timedelta(days=1)
    streak = 0
    while hari.isoformat() in tanggal_ada:
        streak += 1
        hari -= timedelta(days=1)
    return streak


# ---------------- timer sesi ibadah ----------------

def catat_timer(menit):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO timer_log (tanggal, menit) VALUES (?, ?)",
            (date.today().isoformat(), menit))


def total_timer_hari_ini():
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT COALESCE(SUM(menit), 0) FROM timer_log"
            " WHERE tanggal = ?", (date.today().isoformat(),)).fetchone()
    return baris[0]


# ---------------- tasbih (BARU) ----------------

def simpan_tasbih(tanggal, tambahan):
    with sqlite3.connect(DB) as con:
        con.execute("INSERT OR IGNORE INTO tasbih_log (tanggal, hitungan)"
                    " VALUES (?, 0)", (tanggal,))
        con.execute("UPDATE tasbih_log SET hitungan = hitungan + ?"
                    " WHERE tanggal = ?", (tambahan, tanggal))


def ambil_tasbih(tanggal):
    with sqlite3.connect(DB) as con:
        baris = con.execute(
            "SELECT hitungan FROM tasbih_log WHERE tanggal = ?",
            (tanggal,)).fetchone()
    return baris[0] if baris else 0


def reset_tasbih(tanggal):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM tasbih_log WHERE tanggal = ?", (tanggal,))


# ---------------- statistik (BARU) ----------------

def ringkasan_minggu(awal):
    """Total menit timer, tasbih, dan jumlah hari aktif sejak tanggal awal."""
    with sqlite3.connect(DB) as con:
        menit = con.execute(
            "SELECT COALESCE(SUM(menit), 0) FROM timer_log"
            " WHERE tanggal >= ?", (awal,)).fetchone()[0]
        tasbih = con.execute(
            "SELECT COALESCE(SUM(hitungan), 0) FROM tasbih_log"
            " WHERE tanggal >= ?", (awal,)).fetchone()[0]
        hari_aktif = con.execute(
            "SELECT COUNT(DISTINCT tanggal) FROM ceklis_log"
            " WHERE selesai = 1 AND tanggal >= ?", (awal,)).fetchone()[0]
    return menit, tasbih, hari_aktif


def total_keseluruhan():
    with sqlite3.connect(DB) as con:
        menit = con.execute(
            "SELECT COALESCE(SUM(menit), 0) FROM timer_log").fetchone()[0]
        tasbih = con.execute(
            "SELECT COALESCE(SUM(hitungan), 0) FROM tasbih_log").fetchone()[0]
    return menit, tasbih

# ---------------- doa favorit ----------------

def doa_favorit(nomor):
    with sqlite3.connect(DB) as con:
        return con.execute("SELECT 1 FROM doa_favorit WHERE nomor = ?", (nomor,)).fetchone() is not None

def set_doa_favorit(nomor, aktif):
    with sqlite3.connect(DB) as con:
        if aktif:
            con.execute("INSERT OR IGNORE INTO doa_favorit (nomor) VALUES (?)", (nomor,))
        else:
            con.execute("DELETE FROM doa_favorit WHERE nomor = ?", (nomor,))

def semua_doa_favorit():
    with sqlite3.connect(DB) as con:
        return [r[0] for r in con.execute("SELECT nomor FROM doa_favorit ORDER BY nomor").fetchall()]


# ---------------- achievement ----------------

def simpan_achievement(achievement_id, tanggal):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT OR IGNORE INTO achievement (id, tercapai, tanggal) VALUES (?, 1, ?)",
            (achievement_id, tanggal))

def ambil_achievement():
    with sqlite3.connect(DB) as con:
        return {r[0]: r[1] for r in con.execute(
            "SELECT id, tanggal FROM achievement WHERE tercapai = 1").fetchall()}

# ---------------- ayat harian ----------------

def simpan_ayat(tanggal, surah, ayat, teks_arab, teks_indo):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT OR REPLACE INTO ayat_cache VALUES (?, ?, ?, ?, ?)",
            (tanggal, surah, ayat, teks_arab, teks_indo))

def ambil_ayat(tanggal):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return con.execute(
            "SELECT * FROM ayat_cache WHERE tanggal = ?", (tanggal,)).fetchone()

# ---------------- data grafik mingguan ----------------

def data_grafik_mingguan(awal=None):
    """Return data 7 hari terakhir: list of dict {tanggal, menit, tasbih, ceklis_persen}."""
    hasil = []
    for i in range(6, -1, -1):
        hari = date.today() - timedelta(days=i)
        tgl = hari.isoformat()
        with sqlite3.connect(DB) as con:
            menit = con.execute(
                "SELECT COALESCE(SUM(menit), 0) FROM timer_log WHERE tanggal = ?",
                (tgl,)).fetchone()[0]
            tasbih = con.execute(
                "SELECT COALESCE(SUM(hitungan), 0) FROM tasbih_log WHERE tanggal = ?",
                (tgl,)).fetchone()[0]
            status = con.execute(
                "SELECT COUNT(*) FROM ceklis_log WHERE tanggal = ? AND selesai = 1",
                (tgl,)).fetchone()[0]
            total_ceklis = con.execute(
                "SELECT COUNT(*) FROM ceklis WHERE aktif = 1").fetchone()[0]
        persen = int((status / total_ceklis) * 100) if total_ceklis > 0 else 0
        hasil.append({
            "tanggal": tgl,
            "hari": hari.strftime("%a"),
            "menit": menit,
            "tasbih": tasbih,
            "ceklis_persen": persen,
        })
    return hasil
