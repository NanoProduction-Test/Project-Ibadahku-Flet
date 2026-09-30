import asyncio
import math
import sqlite3
import time
from datetime import date, datetime, timedelta

import flet as ft

import achievements
import database as db
import prayertimes
from doa import DOA

# ============================================================
#  DESAIN "ZAMRUD & EMAS" - versi mobile-friendly v5
# ============================================================

GOLD = "#C29B3C"
DANGER = "#B3402E"
FONT_ARAB = "NotoNaskh"

LIGHT = {
    "bg": "#F7F3EA", "surface": "#FFFFFF", "surface2": "#EFE8D9",
    "text": "#1B241F", "muted": "#7C7566", "line": "#E5DCC9",
}
DARK = {
    "bg": "#0D1310", "surface": "#15201A", "surface2": "#1D2B23",
    "text": "#EFEDE3", "muted": "#93A096", "line": "#26362D",
}
ACCENTS = ["#0D5C46", "#155E75", "#8C2F39", "#4C3A8C", "#8A5A24"]

AYAT_HARIAN = [
    ("Al-Insyirah", "94:5", "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "Karena sesungguhnya bersama kesulitan ada kemudahan."),
    ("Ad-Duha", "93:11", "وَأَمَّا بِنِعْمَةِ رَبِّكَ فَحَدِّثْ", "Dan terhadap nikmat Tuhanmu, maka hendaklah engkau nyatakan dengan bersyukur."),
    ("Al-Baqarah", "2:286", "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "Allah tidak membebani seseorang melainkan sesuai dengan kesanggupannya."),
    ("Ar-Ra'd", "13:28", "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "Ingatlah, hanya dengan mengingat Allah hati menjadi tenteram."),
    ("Al-Baqarah", "2:152", "فَاذْكُرُونِي أَذْكُرْكُمْ وَاشْكُرُوا لِي وَلَا تَكْفُرُونِ", "Maka ingatlah kepada-Ku, Aku pun akan ingat kepadamu. Bersyukurlah kepada-Ku dan janganlah kamu ingkar."),
    ("Ali Imran", "3:139", "وَلَا تَهِنُوا وَلَا تَحْزَنُوا وَأَنْتُمُ الْأَعْلَوْنَ إِنْ كُنْتُمْ مُؤْمِنِينَ", "Janganlah kamu lemah dan jangan bersedih hati, padahal kamulah yang paling tinggi jika kamu beriman."),
    ("At-Talaq", "65:3", "وَمَنْ يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ", "Barangsiapa bertawakal kepada Allah, niscaya Allah akan mencukupkan keperluannya."),
]

DZIKIR = ["Subhanallah", "Alhamdulillah", "Allahu Akbar", "La ilaha illallah"]
HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
SINGKAT_HARI = {"Mon": "Sen", "Tue": "Sel", "Wed": "Rab", "Thu": "Kam",
                "Fri": "Jum", "Sat": "Sab", "Sun": "Min"}


def today():
    return date.today().isoformat()


def nama_hari_ini():
    return HARI_ID[date.today().weekday()]


def format_tanggal():
    bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"][date.today().month - 1]
    return f"{nama_hari_ini()}, {date.today().day} {bulan} {date.today().year}"


def ubah_kegiatan(id_kegiatan, nama, jam, hari, kategori):
    """Update kegiatan - ada di main.py supaya database.py tak perlu diedit."""
    with sqlite3.connect(db.DB) as con:
        con.execute(
            "UPDATE kegiatan SET nama=?, jam=?, hari=?, kategori=? WHERE id=?",
            (nama, jam, hari, kategori, id_kegiatan),
        )


class IbadahKu:
    def __init__(self, page: ft.Page):
        self.page = page
        self.index = 0
        db.buat_tabel()
        self.dark = db.ambil_pengaturan("dark_mode", "0") == "1"
        self.accent = db.ambil_pengaturan("accent", ACCENTS[0])
        self.city = db.ambil_pengaturan("kota", "Jakarta")
        self.alarm = db.ambil_pengaturan("alarm", "0") == "1"
        self.prayer = None
        self._prayer_retry_at = 0.0
        self.timer_total = 25 * 60
        self.timer_left = 25 * 60
        self.timer_running = False
        self.timer_task = None
        self.tasbih_count = db.ambil_tasbih(today())
        self.tasbih_target = int(db.ambil_pengaturan("tasbih_target", "33"))
        self.dzikir = db.ambil_pengaturan("dzikir", DZIKIR[0])
        self.search_doa = ""
        self.favorite_only = False
        self._countdown_label = None
        self._hero_nama = None
        self._fokus_time = None
        self._fokus_ring = None
        self._configure_page()

    # ================= tema & komponen dasar =================

    @property
    def c(self):
        return DARK if self.dark else LIGHT

    def _darken(self, hex_color, f=0.6):
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return f"#{int(r * f):02X}{int(g * f):02X}{int(b * f):02X}"

    def _gradient(self):
        return ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[self.accent, self._darken(self.accent)])

    def _center(self, control):
        """Baris selebar kartu yang isinya SELALU lurus tengah."""
        return ft.Row([control], alignment=ft.MainAxisAlignment.CENTER)

    def d_w(self):
        """Lebar dialog responsif - konservatif (dialog punya padding sendiri)."""
        try:
            w = self.page.width or 400
        except Exception:
            w = 400
        return min(w - 72, 440)

    def d_h(self):
        try:
            h = self.page.height or 700
        except Exception:
            h = 700
        return max(240, min(h - 190, 470))

    def card(self, content, *, padding=16, bgcolor=None, radius=20, expand=False,
             gradient=None, border=None, on_click=None, shadow=True):
        return ft.Container(
            content=content, padding=padding, bgcolor=bgcolor or self.c["surface"],
            gradient=gradient, border=border, border_radius=radius, expand=expand,
            on_click=on_click,
            shadow=ft.BoxShadow(blur_radius=18, spread_radius=0, color="#14000000",
                                offset=ft.Offset(0, 4)) if shadow else None)

    def section(self, title, trailing=None):
        return ft.Row([
            ft.Container(width=4, height=18, border_radius=2, bgcolor=GOLD),
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=self.c["text"], expand=True),
            trailing or ft.Container(),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def header(self, title, subtitle=None, action=None):
        return ft.Row([
            ft.Column([
                ft.Text(title, size=25, weight=ft.FontWeight.BOLD, color=self.c["text"]),
                ft.Text(subtitle or format_tanggal(), size=12, color=self.c["muted"]),
            ], spacing=2, expand=True),
            action or ft.Container(),
        ], vertical_alignment=ft.CrossAxisAlignment.START)

    def notify(self, message):
        sb = ft.SnackBar(ft.Text(message, color="#FFFFFF"), bgcolor=self.accent)
        try:
            self.page.show_dialog(sb)
        except Exception:
            self.page.snack_bar = sb
            self.page.update()

    def on_nav(self, e):
        self.index = e.control.selected_index
        self.refresh()

    def _configure_page(self):
        self.page.title = "IbadahKu"
        self.page.padding = 0
        self.page.bgcolor = self.c["bg"]
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark else ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=self.accent, scaffold_bgcolor=self.c["bg"])
        self.page.dark_theme = ft.Theme(color_scheme_seed=self.accent, scaffold_bgcolor=self.c["bg"])
        self.page.fonts = {"NotoNaskh": "assets/fonts/NotoNaskhArabic-Regular.ttf"}
        first = not hasattr(self, "body")
        if first:
            self.body = ft.Container(expand=True, padding=ft.Padding.only(left=14, right=14, top=6, bottom=4))
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=self.index,
            on_change=self.on_nav,
            bgcolor=self.c["surface"],
            indicator_color=self.accent + "26",
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Beranda"),
                ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST_OUTLINED, selected_icon=ft.Icons.CHECKLIST, label="Kegiatan"),
                ft.NavigationBarDestination(icon=ft.Icons.SELF_IMPROVEMENT_OUTLINED, selected_icon=ft.Icons.SELF_IMPROVEMENT, label="Fokus"),
                ft.NavigationBarDestination(icon=ft.Icons.CIRCLE_OUTLINED, selected_icon=ft.Icons.TRIP_ORIGIN, label="Tasbih"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Atur"),
            ],
        )
        if first:
            self.page.add(ft.SafeArea(content=self.body, expand=True))
            self.page.run_task(self._countdown_loop)
        self.refresh()

    def refresh(self):
        self.page.bgcolor = self.c["bg"]
        self.page.navigation_bar.bgcolor = self.c["surface"]
        self.page.navigation_bar.selected_index = self.index
        self.page.navigation_bar.indicator_color = self.accent + "26"
        pages = [self.home_page, self.activities_page, self.focus_page,
                 self.tasbih_page, self.settings_page]
        self.body.content = pages[self.index]()
        self.page.update()

    # ================= Beranda =================

    def get_prayer(self):
        if self.prayer:
            return self.prayer
        if time.time() < self._prayer_retry_at:
            return None
        cached = db.ambil_jadwal(self.city, today())
        if cached:
            self.prayer = cached
            return cached
        try:
            self.prayer = prayertimes.ambil_jadwal(self.city)
            db.simpan_jadwal(self.city, today(), self.prayer)
        except Exception:
            self.prayer = None
            self._prayer_retry_at = time.time() + 30
        return self.prayer

    def next_prayer(self):
        jadwal = self.get_prayer()
        if not jadwal:
            return None, None
        now = datetime.now()
        for name, hm in jadwal:
            h, m = map(int, hm.split(":")[:2])
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target > now:
                return name, target
        name, hm = jadwal[0]
        h, m = map(int, hm.split(":")[:2])
        return name + " (besok)", now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=1)

    def countdown_text(self):
        _, target = self.next_prayer()
        if not target:
            return "--:--:--"
        sec = max(0, int((target - datetime.now()).total_seconds()))
        return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"

    async def _countdown_loop(self):
        while True:
            await asyncio.sleep(1)
            try:
                if self.index == 0:
                    if self._countdown_label is not None:
                        self._countdown_label.value = self.countdown_text()
                        self._countdown_label.update()
                    nama = self.next_prayer()[0] or ""
                    if nama != self._hero_nama:
                        self.refresh()
            except Exception:
                pass

    def home_page(self):
        checks = db.semua_ceklis()
        statuses = db.status_ceklis(today())
        done = sum(1 for r in checks if statuses.get(r["id"], False))
        total = len(checks)
        progress = done / total if total else 0
        next_name, _ = self.next_prayer()
        self._hero_nama = next_name
        ayat = AYAT_HARIAN[date.today().toordinal() % len(AYAT_HARIAN)]
        schedule = self.get_prayer()

        theme_btn = ft.Container(
            content=ft.Icon(ft.Icons.LIGHT_MODE_OUTLINED if self.dark else ft.Icons.DARK_MODE_OUTLINED,
                            size=20, color=self.c["muted"]),
            width=40, height=40, border_radius=20, bgcolor=self.c["surface2"],
            on_click=self.toggle_dark, tooltip="Ganti tema terang/gelap")

        self._countdown_label = ft.Text(self.countdown_text(), size=28,
                                        weight=ft.FontWeight.BOLD, color="#FFFFFF")
        hero = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("SHOLAT BERIKUTNYA", size=11, weight=ft.FontWeight.BOLD, color=GOLD),
                        ft.Text(next_name or "Memuat jadwal...", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ], spacing=2, expand=True),
                    ft.Column([
                        self._countdown_label,
                        ft.Text("menuju adzan", size=11, color="#FFFFFFB0"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=0),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=10),
                ft.Row([
                    ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=13, color="#FFFFFFB0"),
                            ft.Text(self.city, size=12, color="#FFFFFFB0")], spacing=4),
                    ft.Text("Metode Kemenag RI", size=12, color="#FFFFFFB0"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=0),
            padding=20, border_radius=26, gradient=self._gradient(),
            shadow=ft.BoxShadow(blur_radius=24, spread_radius=0, color="#2E000000",
                                offset=ft.Offset(0, 7)))

        berikutnya = (next_name or "").replace(" (besok)", "")
        if schedule:
            pills = []
            for name, hm in schedule:
                aktif = name == berikutnya
                pills.append(ft.Container(
                    content=ft.Column([
                        ft.Text(name, size=11, color=self.accent if aktif else self.c["muted"]),
                        ft.Text(hm, size=15, weight=ft.FontWeight.BOLD,
                                color=self.accent if aktif else self.c["text"]),
                    ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(horizontal=13, vertical=8),
                    bgcolor=GOLD + "26" if aktif else self.c["surface"],
                    border=None if aktif else ft.Border.all(1, self.c["line"]),
                    border_radius=16))
            schedule_row = ft.Row(pills, wrap=True, spacing=6, run_spacing=6,
                                  alignment=ft.MainAxisAlignment.CENTER)
        else:
            schedule_row = ft.Text("Belum ada jadwal. Atur kota di tab Atur atau cek internet.",
                                   size=12, color=self.c["muted"])

        ayat_card = self.card(ft.Column([
            ft.Row([
                ft.Container(content=ft.Icon(ft.Icons.FORMAT_QUOTE, size=15, color=GOLD),
                             width=32, height=32, border_radius=16, bgcolor=GOLD + "22",
                             alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text("Ayat Hari Ini", size=14, weight=ft.FontWeight.BOLD, color=self.c["text"]),
                    ft.Text(f"{ayat[0]} · {ayat[1]}", size=11, color=self.c["muted"]),
                ], spacing=1, expand=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=6),
            ft.Text(ayat[2], size=22, font_family=FONT_ARAB, text_align=ft.TextAlign.RIGHT, color=self.c["text"]),
            ft.Container(height=4),
            ft.Text(f"“{ayat[3]}”", size=12, color=self.c["muted"], italic=True),
        ]))

        donut = ft.Stack([
            ft.ProgressRing(value=progress, width=72, height=72, stroke_width=8,
                            color=GOLD, bgcolor=self.c["surface2"]),
            ft.Container(width=72, height=72, alignment=ft.Alignment.CENTER,
                         content=ft.Text(f"{done}/{total}", size=14, weight=ft.FontWeight.BOLD,
                                         color=self.c["text"])),
        ], width=72, height=72)
        checklist_rows = []
        for item in checks:
            selesai = statuses.get(item["id"], False)
            checklist_rows.append(ft.Container(
                content=ft.Row([
                    ft.Checkbox(value=selesai, active_color=self.accent,
                                on_change=lambda e, iid=item["id"]: self.toggle_check(iid, e.control.value)),
                    ft.Text(item["nama"], size=13, color=self.c["text"], expand=True,
                            style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if selesai else None),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(horizontal=8, vertical=0),
                bgcolor=self.accent + "14" if selesai else self.c["surface2"],
                border_radius=12))
        checklist_card = self.card(ft.Column([
            self.section("Checklist Hari Ini"),
            ft.Row([donut, ft.Column([
                ft.Text(f"{int(progress * 100)}% selesai hari ini", size=13,
                        weight=ft.FontWeight.BOLD, color=self.c["text"]),
                ft.Text("Tandai ibadahmu untuk menjaga streak", size=11, color=self.c["muted"]),
            ], spacing=2, expand=True)], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            *checklist_rows,
        ], spacing=5))

        return ft.Column([
            self.header("Assalamu'alaikum 👋", f"{format_tanggal()} · {self.city}", action=theme_btn),
            ft.Container(height=4), hero,
            self.section("Jadwal Sholat"), schedule_row,
            ayat_card,
            checklist_card,
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def toggle_check(self, item_id, value):
        db.set_ceklis(item_id, today(), value)
        achievements.evaluasi()
        self.refresh()

    # ================= Kegiatan =================

    def hapus_kecil(self, row):
        """Tombol X kecil - dengan dialog konfirmasi (anti hapus tak sengaja)."""
        return ft.Container(
            content=ft.Icon(ft.Icons.CLOSE, size=15, color=DANGER),
            width=36, height=36, border_radius=18,
            alignment=ft.Alignment.CENTER, tooltip="Hapus",
            on_click=lambda e: self.konfirmasi_hapus(row))

    def konfirmasi_hapus(self, row, dialog_induk=None):
        """Dialog 'yakin hapus?' - dipakai tombol X maupun tombol Hapus di form."""

        def ya(e=None):
            db.hapus(row["id"])
            self.close_dialog(konfirmasi)
            if dialog_induk is not None:
                self.close_dialog(dialog_induk)
            self.notify("Kegiatan dihapus")
            self.refresh()

        konfirmasi = ft.AlertDialog(
            modal=True, title=ft.Text("Hapus kegiatan?"),
            content=ft.Text(f'"{row["nama"]}" akan dihapus permanen.'),
            actions=[
                ft.TextButton("Batal", on_click=lambda e: self.close_dialog(konfirmasi)),
                ft.FilledButton("Hapus", bgcolor=DANGER, on_click=ya),
            ])
        self.page.show_dialog(konfirmasi)

    def tombol_selesai(self, iid, done):
        """Tombol centang lingkaran 44px - pengganti Checkbox bawaan."""
        return ft.Container(
            content=ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED,
                            size=26, color=self.accent if done else self.c["muted"]),
            width=44, height=44, border_radius=22, alignment=ft.Alignment.CENTER,
            bgcolor=self.accent + "1A" if done else None,
            tooltip="Tandai selesai",
            on_click=lambda e: self.set_activity(iid, not done))

    def empty_state(self, judul, pesan):
        """Kartu keadaan kosong - SEMUA isinya digaransi lurus tengah
        lewat pola _center() (tiap elemen dibungkus baris selebar kartu)."""
        return self.card(ft.Column([
            self._center(ft.Container(
                content=ft.Icon(ft.Icons.EVENT_AVAILABLE_OUTLINED, size=26, color=GOLD),
                width=52, height=52, border_radius=26, bgcolor=GOLD + "1A",
                alignment=ft.Alignment.CENTER)),
            self._center(ft.Text(judul, size=14, weight=ft.FontWeight.BOLD,
                                 color=self.c["text"],
                                 text_align=ft.TextAlign.CENTER)),
            self._center(ft.Text(pesan, size=12, color=self.c["muted"],
                                 text_align=ft.TextAlign.CENTER)),
        ], spacing=6), padding=18)

    def activities_page(self):
        rows = db.kegiatan_hari_ini(nama_hari_ini())
        status = db.status_kegiatan(today())
        semua = db.semua()
        tambah_btn = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.ADD, size=15, color=GOLD),
                            ft.Text("Tambah", size=13, weight=ft.FontWeight.BOLD, color=GOLD)],
                           spacing=4),
            border=ft.Border.all(1.5, GOLD), border_radius=999,
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            on_click=lambda e: self.open_form_kegiatan())
        controls = [
            self.header("Kegiatan", "Rutinitas & target pribadimu"),
            self.section("Hari Ini", trailing=tambah_btn),
        ]
        if not rows:
            pesan = ("Tidak ada kegiatan terjadwal untuk hari ini.\n"
                     "Kegiatan lainnya ada di daftar bawah.") if semua else \
                "Tekan + Tambah untuk membuat rutinitas baru."
            controls.append(self.empty_state("Belum ada kegiatan hari ini", pesan))
        for row in rows:
            controls.append(self.activity_card(row, status.get(row["id"], False)))
        hitung = ft.Text(f"{len(semua)} total", size=12,
                         color=self.c["muted"]) if semua else None
        controls.append(self.section("Semua Kegiatan", trailing=hitung))
        controls.extend(self.all_activity_cards())
        return ft.Column(controls, scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)

    def activity_card(self, row, done):
        """Kartu Hari Ini: tap kartu = edit, lingkaran = selesai, X = hapus."""
        return self.card(ft.Row([
            self.tombol_selesai(row["id"], done),
            ft.Column([
                ft.Text(row["nama"], size=14, weight=ft.FontWeight.BOLD,
                        color=self.c["text"], max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None),
                ft.Text(f"{row['jam']} · {row['kategori']}", size=11, color=self.c["muted"]),
            ], spacing=2, expand=True),
            self.hapus_kecil(row),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=8, on_click=lambda e: self.open_form_kegiatan(data=row))

    def all_activity_cards(self):
        """Kartu Semua Kegiatan: tap kartu = edit, X = hapus."""
        rows = db.semua()
        if not rows:
            return [self.card(ft.Column([
                self._center(ft.Text("Belum ada kegiatan tersimpan.", size=13,
                                     color=self.c["muted"],
                                     text_align=ft.TextAlign.CENTER)),
                self._center(ft.Text("Tekan + Tambah untuk membuat yang pertama.",
                                     size=11, color=self.c["muted"],
                                     text_align=ft.TextAlign.CENTER)),
            ], spacing=2), padding=16)]
        out = []
        for row in rows:
            hari_ini = row["hari"] in ("Setiap hari", nama_hari_ini())
            info = ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            if hari_ini:
                info.controls.append(ft.Container(width=7, height=7, border_radius=4, bgcolor=GOLD))
            info.controls.append(ft.Text(f"{row['jam']} · {row['hari']} · {row['kategori']}",
                                         size=11, color=self.c["muted"]))
            out.append(self.card(ft.Row([
                ft.Column([
                    ft.Text(row["nama"], size=14, weight=ft.FontWeight.BOLD,
                            color=self.c["text"], max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    info,
                ], spacing=2, expand=True),
                ft.Icon(ft.Icons.EDIT_OUTLINED, size=15, color=self.c["muted"]),
                self.hapus_kecil(row),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10,
                on_click=lambda e, r=row: self.open_form_kegiatan(data=r)))
        return out

    def open_form_kegiatan(self, e=None, data=None):
        """Form tambah/edit kegiatan.
        Hari & kategori memakai CHIP (bukan dropdown) - andal di HP."""
        edit = data is not None
        name = ft.TextField(label="Nama kegiatan", autofocus=True,
                            value=data["nama"] if edit else "", border_radius=14)
        jam = ft.TextField(label="Jam (contoh 19:30)",
                           value=data["jam"] if edit else "19:00", border_radius=14)
        pilihan = {"hari": data["hari"] if edit else "Setiap hari",
                   "kategori": data["kategori"] if edit else "Pribadi"}

        def chip_row(judul, opsi, kunci):
            def buat(label):
                aktif = pilihan[kunci] == label
                return ft.Container(
                    content=ft.Text(label, size=12, weight=ft.FontWeight.BOLD,
                                    color="#FFFFFF" if aktif else self.c["text"]),
                    bgcolor=self.accent if aktif else None,
                    border=None if aktif else ft.Border.all(1, self.c["line"]),
                    border_radius=999,
                    padding=ft.Padding.symmetric(horizontal=13, vertical=8),
                    on_click=lambda e, l=label: pilih(l))

            row = ft.Row([buat(x) for x in opsi], wrap=True, spacing=6, run_spacing=6)

            def pilih(label):
                pilihan[kunci] = label
                row.controls = [buat(x) for x in opsi]
                try:
                    self.page.update()
                except Exception:
                    pass

            return ft.Column([ft.Text(judul, size=12, color=self.c["muted"]), row],
                             spacing=6)

        def simpan(e=None):
            nama = name.value.strip()
            nilai_jam = jam.value.strip()
            name.error_text = None
            jam.error_text = None
            if not nama:
                name.error_text = "Nama belum diisi"
                self.page.update()
                return
            try:
                bagian = nilai_jam.split(":")
                h, m = int(bagian[0]), int(bagian[1])
                valid = len(bagian) == 2 and 0 <= h <= 23 and 0 <= m <= 59
            except (ValueError, IndexError):
                valid = False
            if not valid:
                jam.error_text = "Format jam: HH:MM (contoh 19:30)"
                self.page.update()
                return
            jam_rapi = f"{h:02d}:{m:02d}"
            if edit:
                ubah_kegiatan(data["id"], nama, jam_rapi,
                              pilihan["hari"], pilihan["kategori"])
                self.notify("Kegiatan diperbarui")
            else:
                db.tambah(nama, jam_rapi, pilihan["hari"], pilihan["kategori"])
                self.notify("Kegiatan ditambahkan")
            self.close_dialog(dlg)
            self.refresh()

        actions = [ft.TextButton("Batal", on_click=lambda e: self.close_dialog(dlg))]
        if edit:
            actions.append(ft.TextButton(
                "Hapus", style=ft.ButtonStyle(color=DANGER),
                on_click=lambda e: self.konfirmasi_hapus(data, dlg)))
        actions.append(ft.FilledButton("Simpan", on_click=simpan, bgcolor=self.accent))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Kegiatan" if edit else "Tambah Kegiatan"),
            content=ft.Column([
                name, jam,
                chip_row("Hari", ["Setiap hari"] + HARI_ID, "hari"),
                chip_row("Kategori",
                         ["Pribadi", "Ibadah", "Belajar", "Kesehatan", "Lainnya"],
                         "kategori"),
            ], spacing=14, tight=True, width=self.d_w() - 40),
            actions=actions)
        self.page.show_dialog(dlg)

    def close_dialog(self, dlg):
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    def set_activity(self, iid, value):
        db.set_kegiatan_selesai(iid, today(), value)
        self.refresh()

    # ================= Fokus (timer) =================

    def focus_page(self):
        mins = self.timer_total // 60
        progress = 1 - self.timer_left / self.timer_total if self.timer_total else 0
        self._fokus_ring = ft.ProgressRing(value=progress, width=200, height=200,
                                           stroke_width=13, color=GOLD,
                                           bgcolor=self.c["surface2"])
        self._fokus_time = ft.Text(f"{self.timer_left // 60:02d}:{self.timer_left % 60:02d}",
                                   size=40, weight=ft.FontWeight.BOLD, color=self.c["text"])
        status_chip = ft.Container(
            content=ft.Text("BERJALAN" if self.timer_running else "SIAP", size=10,
                            weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            bgcolor=self.accent if self.timer_running else self.c["muted"],
            border_radius=999, padding=ft.Padding.symmetric(horizontal=12, vertical=4))
        ring_stack = ft.Stack([
            self._fokus_ring,
            ft.Container(width=200, height=200, alignment=ft.Alignment.CENTER,
                         content=ft.Column([
                             self._fokus_time,
                             status_chip,
                         ], alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)),
        ], width=200, height=200)
        duration_options = [5, 10, 15, 25, 30, 45, 60]
        chips = ft.Row([
            ft.Container(
                content=ft.Text(f"{m} m", size=12, weight=ft.FontWeight.BOLD,
                                color="#FFFFFF" if mins == m else self.c["text"]),
                bgcolor=self.accent if mins == m else None,
                border=None if mins == m else ft.Border.all(1, self.c["line"]),
                border_radius=999, padding=ft.Padding.symmetric(horizontal=13, vertical=7),
                on_click=lambda e, x=m: self.set_timer_minutes(x))
            for m in duration_options], wrap=True, spacing=6, run_spacing=6,
            alignment=ft.MainAxisAlignment.CENTER)
        return ft.Column([
            self.header("Fokus Ibadah", "Tenang, khusyuk, tanpa distraksi"),
            self.card(ft.Column([
                ft.Text("Durasi", size=12, color=self.c["muted"], text_align=ft.TextAlign.CENTER),
                chips,
                ft.Container(height=10),
                self._center(ring_stack),
                ft.Container(height=12),
                ft.Row([
                    ft.FilledButton("Mulai" if not self.timer_running else "Jeda",
                                    icon=ft.Icons.PLAY_ARROW if not self.timer_running else ft.Icons.PAUSE,
                                    on_click=self.toggle_timer, bgcolor=self.accent, height=44),
                    ft.OutlinedButton("Reset", icon=ft.Icons.RESTART_ALT,
                                      on_click=self.reset_timer, height=44),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Container(height=6),
                self._center(ft.Container(
                    content=ft.Text(f"Total hari ini: {db.total_timer_hari_ini()} menit",
                                    size=12, color=self.c["muted"]),
                    bgcolor=self.c["surface2"], border_radius=999,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=5))),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20),
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def _update_fokus_ui(self):
        try:
            if self._fokus_time is not None:
                self._fokus_time.value = (f"{self.timer_left // 60:02d}:"
                                          f"{self.timer_left % 60:02d}")
                self._fokus_time.update()
            if self._fokus_ring is not None and self.timer_total:
                self._fokus_ring.value = max(0.0, min(1.0, 1 - self.timer_left / self.timer_total))
                self._fokus_ring.update()
        except Exception:
            pass

    def set_timer_minutes(self, minutes):
        if self.timer_running:
            return
        self.timer_total = minutes * 60
        self.timer_left = self.timer_total
        self.refresh()

    def toggle_timer(self, e=None):
        if self.timer_running:
            self.timer_running = False
            self.refresh()
            return
        if self.timer_left <= 0:
            self.timer_left = self.timer_total
        self.timer_running = True
        self.refresh()
        self.timer_task = self.page.run_task(self._timer_loop)

    async def _timer_loop(self):
        while self.timer_running and self.timer_left > 0:
            await asyncio.sleep(1)
            if not self.timer_running:
                return
            self.timer_left -= 1
            self._update_fokus_ui()
        self.timer_running = False
        db.catat_timer(self.timer_total // 60)
        achievements.evaluasi()
        self.notify("Sesi timer selesai. Alhamdulillah.")
        self.refresh()

    def reset_timer(self, e=None):
        self.timer_running = False
        self.timer_left = self.timer_total
        self.refresh()

    # ================= Tasbih =================

    def tasbih_page(self):
        progress = min(1, self.tasbih_count / self.tasbih_target) if self.tasbih_target else 0
        sisa = max(0, self.tasbih_target - self.tasbih_count)
        tercapai = self.tasbih_count > 0 and self.tasbih_count >= self.tasbih_target

        lit = self.tasbih_count % 33
        if lit == 0 and self.tasbih_count > 0:
            lit = 33
        R = 95
        beads = []
        for i in range(33):
            a = 2 * math.pi * i / 33 - math.pi / 2
            x, y = R + 79 * math.cos(a), R + 79 * math.sin(a)
            beads.append(ft.Container(width=9, height=9, border_radius=9,
                                      bgcolor=self.accent if i < lit else self.c["line"],
                                      left=x - 4.5, top=y - 4.5))
        tengah = ft.Container(width=2 * R, height=2 * R, alignment=ft.Alignment.CENTER,
                              content=ft.Column([
                                  ft.Text(str(self.tasbih_count), size=42,
                                          weight=ft.FontWeight.BOLD, color=self.accent),
                                  ft.Text(f"dari {self.tasbih_target}", size=12,
                                          color=self.c["muted"]),
                              ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 alignment=ft.MainAxisAlignment.CENTER, spacing=0))
        ring = ft.Container(content=ft.Stack([*beads, tengah], width=2 * R, height=2 * R),
                            width=2 * R, height=2 * R, border_radius=R,
                            bgcolor=self.c["surface2"], on_click=self.tap_tasbih)

        if tercapai:
            status_chip = ft.Container(
                content=ft.Text("TARGET TERCAPAI · MASYAALLAH", size=11,
                                weight=ft.FontWeight.BOLD, color=GOLD),
                bgcolor=GOLD + "22", border_radius=999,
                padding=ft.Padding.symmetric(horizontal=12, vertical=5))
        else:
            status_chip = ft.Container(
                content=ft.Text(f"Sisa {sisa} lagi", size=12, color=self.c["muted"]),
                bgcolor=self.c["surface2"], border_radius=999,
                padding=ft.Padding.symmetric(horizontal=12, vertical=5))

        tap_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.TOUCH_APP, color="#FFFFFF", size=22),
                ft.Text("TAP UNTUK BERHITUNG", color="#FFFFFF", size=13,
                        weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            height=52, border_radius=26, gradient=self._gradient(),
            on_click=self.tap_tasbih, alignment=ft.Alignment.CENTER)

        return ft.Column([
            self.header("Tasbih Digital", f"{self.dzikir} · target {self.tasbih_target}"),
            self.card(ft.Column([
                self._center(ft.Text(self.dzikir, size=18, weight=ft.FontWeight.BOLD,
                                     color=self.c["text"])),
                ft.Container(height=8),
                ft.ProgressBar(value=progress, color=GOLD,
                               bgcolor=self.c["surface2"], height=7),
                ft.Container(height=12),
                self._center(ring),
                ft.Container(height=12),
                self._center(status_chip),
                ft.Container(height=14),
                tap_btn,
                ft.Container(height=10),
                ft.Row([
                    ft.OutlinedButton("Reset", icon=ft.Icons.RESTART_ALT,
                                      on_click=self.reset_tasbih, expand=True),
                    ft.OutlinedButton("Target", icon=ft.Icons.FLAG_OUTLINED,
                                      on_click=self.choose_target, expand=True),
                ], spacing=8),
            ], spacing=0), padding=18),
            self.card(ft.Column([
                self.section("Pilih Dzikir"),
                ft.Row([ft.Chip(label=x, selected=x == self.dzikir, show_checkmark=True,
                                on_select=lambda e, x=x: self.set_dzikir(x)) for x in DZIKIR],
                       wrap=True, spacing=8, run_spacing=8,
                       alignment=ft.MainAxisAlignment.CENTER),
            ])),
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def tap_tasbih(self, e=None):
        self.tasbih_count += 1
        db.simpan_tasbih(today(), 1)
        if self.tasbih_count == self.tasbih_target:
            self.notify("Target tercapai. MasyaAllah!")
        achievements.evaluasi()
        self.refresh()

    def reset_tasbih(self, e=None):
        self.tasbih_count = 0
        db.reset_tasbih(today())
        self.refresh()

    def choose_target(self, e=None):
        dd = ft.Dropdown(label="Target", value=str(self.tasbih_target), border_radius=14,
                         options=[ft.DropdownOption(str(x)) for x in [33, 99, 100, 333, 1000]])

        def save(e):
            self.tasbih_target = int(dd.value)
            db.simpan_pengaturan("tasbih_target", dd.value)
            self.close_dialog(dlg)
            self.refresh()

        dlg = ft.AlertDialog(modal=True, title=ft.Text("Target Tasbih"), content=dd,
                             actions=[ft.TextButton("Batal", on_click=lambda e: self.close_dialog(dlg)),
                                      ft.FilledButton("Simpan", on_click=save, bgcolor=self.accent)])
        self.page.show_dialog(dlg)

    def set_dzikir(self, value):
        self.dzikir = value
        db.simpan_pengaturan("dzikir", value)
        self.refresh()

    # ================= Atur =================

    def action_tile(self, icon, label, on_click):
        return self.card(ft.Row([
            ft.Container(content=ft.Icon(icon, size=20, color=GOLD),
                         width=40, height=40, border_radius=13, bgcolor=GOLD + "1E",
                         alignment=ft.Alignment.CENTER),
            ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=self.c["text"]),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=12, on_click=on_click, expand=True)

    def settings_page(self):
        accent_row = ft.Row([
            ft.Container(width=32, height=32, border_radius=16, bgcolor=c,
                         border=ft.Border.all(3, GOLD) if self.accent == c else None,
                         on_click=lambda e, c=c: self.set_accent(c))
            for c in ACCENTS], spacing=10)
        return ft.Column([
            self.header("Pengaturan", "Personalisasi IbadahKu"),
            self.card(ft.Column([
                self.section("Tampilan"),
                ft.Switch(label="Mode gelap", value=self.dark, active_color=self.accent,
                          on_change=self.toggle_dark),
                ft.Container(height=4),
                ft.Text("Warna aksen", size=12, color=self.c["muted"]),
                accent_row,
            ], spacing=6)),
            self.card(ft.Column([
                self.section("Lokasi & Jadwal Sholat"),
                ft.Dropdown(label="Kota", value=self.city, border_radius=14,
                            options=[ft.DropdownOption(x) for x in sorted(prayertimes.KOTA_KOORDINAT.keys())],
                            on_select=self.set_city),
                ft.Text("Jadwal dari AlAdhan (metode Kemenag). Tanpa internet, cache terakhir dipakai.",
                        size=11, color=self.c["muted"]),
            ], spacing=6)),
            self.card(ft.Column([
                self.section("Pengingat"),
                ft.Switch(label="Pengingat sholat saat aplikasi aktif", value=self.alarm,
                          active_color=self.accent, on_change=self.toggle_alarm),
                ft.Text("Versi web/desktop hanya mengingatkan selama aplikasi terbuka.",
                        size=11, color=self.c["muted"]),
            ], spacing=6)),
            ft.Row([
                self.action_tile(ft.Icons.MENU_BOOK_OUTLINED, "Doa Harian", self.open_doa),
                self.action_tile(ft.Icons.EXPLORE_OUTLINED, "Arah Kiblat", self.open_kiblat),
            ], spacing=8),
            ft.Row([
                self.action_tile(ft.Icons.INSERT_CHART_OUTLINED, "Statistik", self.open_stats),
                self.action_tile(ft.Icons.EMOJI_EVENTS_OUTLINED, "Pencapaian", self.open_badges),
            ], spacing=8),
            ft.Container(height=4),
            ft.Text("IbadahKu · dibuat dengan Flet", size=11, color=self.c["muted"],
                    text_align=ft.TextAlign.CENTER),
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

    def toggle_dark(self, e=None):
        val = getattr(getattr(e, "control", None), "value", None)
        self.dark = (not self.dark) if val is None else val
        db.simpan_pengaturan("dark_mode", "1" if self.dark else "0")
        self._configure_page()

    def set_accent(self, color):
        self.accent = color
        db.simpan_pengaturan("accent", color)
        self._configure_page()

    def set_city(self, e):
        self.city = e.control.value
        db.simpan_pengaturan("kota", self.city)
        self.prayer = None
        self.refresh()

    def toggle_alarm(self, e):
        self.alarm = e.control.value
        db.simpan_pengaturan("alarm", "1" if self.alarm else "0")
        self.notify("Pengingat diaktifkan" if self.alarm else "Pengingat dimatikan")

    # ================= Dialog: Doa =================

    def open_doa(self, e=None):
        self.search_doa = ""
        self.favorite_only = False
        search = ft.TextField(label="Cari doa", prefix_icon=ft.Icons.SEARCH, border_radius=14,
                              on_change=lambda e: self.render_doa_dialog(body, search.value))
        fav = ft.Checkbox(label="Favorit saja", active_color=GOLD,
                          on_change=lambda e: self.toggle_fav_filter(body, e.control.value))
        body = ft.Column([], scroll=ft.ScrollMode.AUTO, height=self.d_h())
        self.render_doa_dialog(body, "")
        dlg = ft.AlertDialog(modal=True, title=ft.Text("Doa Harian"),
                             content=ft.Column([search, fav, body], tight=True, width=self.d_w()),
                             actions=[ft.TextButton("Tutup", on_click=lambda e: self.close_dialog(dlg))])
        self.page.show_dialog(dlg)

    def toggle_fav_filter(self, body, value):
        self.favorite_only = value
        self.render_doa_dialog(body, self.search_doa)

    def render_doa_dialog(self, body, query):
        self.search_doa = query.lower()
        favs = set(db.semua_doa_favorit())
        items = []
        for i, d in enumerate(DOA[:24]):
            if self.favorite_only and i not in favs:
                continue
            if self.search_doa and self.search_doa not in (d["judul"] + " " + d["latin"] + " " + d["arti"]).lower():
                continue
            star = ft.IconButton(icon=ft.Icons.STAR if i in favs else ft.Icons.STAR_BORDER,
                                 icon_color=GOLD if i in favs else self.c["muted"],
                                 on_click=lambda e, i=i: self.toggle_favorite(i, body))
            items.append(self.card(ft.Column([
                ft.Row([
                    ft.Container(content=ft.Text(str(i + 1), size=11, weight=ft.FontWeight.BOLD, color=GOLD),
                                 width=24, height=24, border_radius=12, bgcolor=GOLD + "1E",
                                 alignment=ft.Alignment.CENTER),
                    ft.Text(d["judul"], size=13, weight=ft.FontWeight.BOLD, color=self.c["text"], expand=True),
                    star]),
                ft.Text(d["arab"], size=20, font_family=FONT_ARAB,
                        text_align=ft.TextAlign.RIGHT, color=self.c["text"]),
                ft.Text(d["latin"], size=11, color=self.c["muted"], italic=True),
                ft.Text(d["arti"], size=12, color=self.c["text"]),
            ], spacing=5), padding=12))
        body.controls = items or [ft.Text("Doa tidak ditemukan.", color=self.c["muted"])]
        try:
            self.page.update()
        except Exception:
            pass

    def toggle_favorite(self, i, body):
        active = not db.doa_favorit(i)
        db.set_doa_favorit(i, active)
        self.render_doa_dialog(body, self.search_doa)

    # ================= Dialog: Kiblat =================

    def open_kiblat(self, e=None):
        lat, lon = prayertimes.KOTA_KOORDINAT.get(self.city, (-6.2, 106.82))
        bearing = prayertimes.arah_kiblat(lat, lon)
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text("Arah Kiblat"),
            content=ft.Column([
                self.compass_widget(bearing),
                ft.Text(f"{bearing:.1f}° dari utara · {self.city}", size=14,
                        weight=ft.FontWeight.BOLD, color=self.c["text"],
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Hadap ke arah UTARA, lalu putar searah jarum jam\nsebesar sudut di atas.",
                        size=12, color=self.c["muted"], text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, width=260),
            actions=[ft.TextButton("Tutup", on_click=lambda e: self.close_dialog(dlg))])
        self.page.show_dialog(dlg)

    def compass_widget(self, bearing):
        marks = []
        for angle, label in [(0, "U"), (90, "T"), (180, "S"), (270, "B")]:
            rad = math.radians(angle - 90)
            x = 110 + 86 * math.cos(rad)
            y = 110 + 86 * math.sin(rad)
            marks.append(ft.Container(
                content=ft.Text(label, size=14, weight=ft.FontWeight.BOLD,
                                color=GOLD if label == "U" else self.c["muted"]),
                left=x - 10, top=y - 10, width=20, height=20,
                alignment=ft.Alignment.CENTER))
        needle = ft.Container(
            width=220, height=220, alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.NAVIGATION, size=64, color=DANGER,
                            rotate=ft.Rotate(angle=math.radians(bearing))))
        return ft.Container(
            content=ft.Stack([
                ft.Container(width=220, height=220, border_radius=110,
                             bgcolor=self.c["surface2"],
                             border=ft.Border.all(2, GOLD + "66")),
                *marks, needle,
                ft.Container(width=14, height=14, border_radius=7, bgcolor=GOLD,
                             left=103, top=103),
            ], width=220, height=220),
            padding=10)

    # ================= Dialog: Statistik & Pencapaian =================

    def open_stats(self, e=None):
        w = self.d_w()
        data = db.data_grafik_mingguan()
        maxv = max(1, max(x["menit"] for x in data))
        bars = []
        for x in data:
            h = max(8, int(110 * x["menit"] / maxv))
            bars.append(ft.Column([
                ft.Container(width=22, height=h, bgcolor=GOLD, border_radius=8),
                ft.Text(SINGKAT_HARI.get(x["hari"], x["hari"]), size=10, color=self.c["muted"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.END, spacing=4))
        menit, tasbih, aktif = db.ringkasan_minggu((date.today() - timedelta(days=6)).isoformat())
        tiles = ft.Row([
            self.stat_tile("Menit fokus", str(menit)),
            self.stat_tile("Tasbih", str(tasbih)),
            self.stat_tile("Hari aktif", str(aktif)),
        ], spacing=8)
        content = ft.Column([
            tiles,
            ft.Text("Fokus 7 Hari", size=15, weight=ft.FontWeight.BOLD, color=self.c["text"]),
            ft.Container(ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_AROUND,
                                vertical_alignment=ft.CrossAxisAlignment.END),
                         height=150, bgcolor=self.c["surface2"], border_radius=16, padding=10),
            ft.Text("Grafik memakai menit timer yang tersimpan.", size=11, color=self.c["muted"]),
        ], width=w, spacing=14)
        dlg = ft.AlertDialog(modal=True, title=ft.Text("Statistik 7 Hari"), content=content,
                             actions=[ft.TextButton("Tutup", on_click=lambda e: self.close_dialog(dlg))])
        self.page.show_dialog(dlg)

    def stat_tile(self, label, value):
        return ft.Container(
            content=ft.Column([
                ft.Text(value, size=21, weight=ft.FontWeight.BOLD, color=self.accent),
                ft.Text(label, size=10, color=self.c["muted"]),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=12, bgcolor=self.c["surface2"], border_radius=16, expand=True)

    def badge_tile(self, b):
        """Tile pencapaian dengan expand=True - mustahil overflow."""
        unlocked = b["tercapai"]
        return ft.Container(
            content=ft.Column([
                ft.Text(b["emoji"], size=24, opacity=1.0 if unlocked else 0.4),
                ft.Text(b["judul"], size=11, weight=ft.FontWeight.BOLD,
                        color=self.c["text"], text_align=ft.TextAlign.CENTER),
                ft.Text(b["deskripsi"], size=9, color=self.c["muted"],
                        text_align=ft.TextAlign.CENTER),
            ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=8, border_radius=16, expand=True,
            bgcolor=GOLD + "1A" if unlocked else self.c["surface2"],
            border=ft.Border.all(1.5, GOLD) if unlocked else None)

    def open_badges(self, e=None):
        achievements.evaluasi()
        badges = achievements.semua_dengan_status()
        w = self.d_w()
        cols = 3 if w >= 420 else 2      # 2 kolom di HP, 3 di layar lebar
        rows = []
        for i in range(0, len(badges), cols):
            rows.append(ft.Row([self.badge_tile(b) for b in badges[i:i + cols]],
                               spacing=8))
        dlg = ft.AlertDialog(modal=True, title=ft.Text("Pencapaian"),
                             content=ft.Column(rows, scroll=ft.ScrollMode.AUTO,
                                               height=self.d_h(), width=w, spacing=8),
                             actions=[ft.TextButton("Tutup", on_click=lambda e: self.close_dialog(dlg))])
        self.page.show_dialog(dlg)


def main(page: ft.Page):
    IbadahKu(page)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)