import datetime
import math
import os
import re
import struct
import threading
import wave

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import database as db
import prayertimes
from doa import DOA

Config.set("graphics", "width", "400")
Config.set("graphics", "height", "700")

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Ahad"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

KOTA_DEFAULT = "Jakarta"
DAFTAR_KOTA = [
    "Jakarta", "Bandung", "Bekasi", "Bogor", "Tangerang", "Depok",
    "Semarang", "Yogyakarta", "Surabaya", "Malang",
    "Medan", "Palembang", "Makassar", "Denpasar",
]

try:
    from plyer import notification
except ImportError:
    notification = None

# merangkai tulisan Arab agar tersambung & arahnya benar
try:
    from importlib import import_module

    arabic_reshaper = import_module("arabic_reshaper")
    get_display = import_module("bidi.algorithm").get_display

    def siapkan_arab(teks):
        return get_display(arabic_reshaper.reshape(teks))
except ImportError:
    def siapkan_arab(teks):
        return teks


def kirim_notif(judul, pesan):
    if notification is None:
        return
    try:
        notification.notify(title=judul, message=pesan,
                            app_name="IbadahKu", timeout=10)
    except Exception:
        pass


def cari_font_arab():
    """Cari font yang mendukung huruf Arab di komputer ini."""
    for p in ("font/arab.ttf", "C:/Windows/Fonts/segoeui.ttf",
              "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(p):
            return p
    return "data/fonts/Roboto-Regular.ttf"


def buat_file_bunyi(nama="beep.wav"):
    """Bikin sendiri file bunyi alarm (3x beep) - tanpa file eksternal."""
    if os.path.exists(nama):
        return nama
    fr, dur, jeda, n = 44100, 0.15, 0.12, 3
    siklus = dur + jeda
    with wave.open(nama, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fr)
        for i in range(int(fr * siklus * n)):
            t = i / fr
            fase = t % siklus
            nyala = fase < dur
            amp = math.sin(math.pi * fase / dur) if nyala else 0.0
            v = int(11000 * amp * math.sin(2 * math.pi * 880 * t))
            w.writeframes(struct.pack("<h", v))
    return nama


def _baca_jadwal_cache():
    kota = db.ambil_pengaturan("kota", KOTA_DEFAULT)
    lat = db.ambil_pengaturan("lat")
    kunci = ("auto:" + kota) if lat else kota
    return db.ambil_jadwal(kunci, datetime.date.today().isoformat())


class Tema:
    """Pusat semua warna IbadahKu."""

    terang = {
        "latar": (0.95, 0.96, 0.95, 1), "kartu": (1, 1, 1, 1),
        "utama": (0.13, 0.45, 0.36, 1), "utama_muda": (0.85, 0.93, 0.87, 1),
        "netral": (0.93, 0.93, 0.95, 1), "nav": (0.88, 0.92, 0.89, 1),
        "teks": (0.13, 0.15, 0.14, 1), "teks_pudar": (0.45, 0.48, 0.46, 1),
        "aksen": (1, 0.95, 0.8, 1), "putih": (1, 1, 1, 1),
    }
    gelap = {
        "latar": (0.09, 0.11, 0.10, 1), "kartu": (0.16, 0.19, 0.18, 1),
        "utama": (0.16, 0.40, 0.33, 1), "utama_muda": (0.22, 0.35, 0.29, 1),
        "netral": (0.20, 0.22, 0.21, 1), "nav": (0.20, 0.24, 0.22, 1),
        "teks": (0.92, 0.95, 0.93, 1), "teks_pudar": (0.60, 0.65, 0.62, 1),
        "aksen": (0.95, 0.87, 0.6, 1), "putih": (1, 1, 1, 1),
    }
    warna = terang

    @classmethod
    def muat(cls):
        gelap = db.ambil_pengaturan("mode_gelap", "0") == "1"
        cls.warna = cls.gelap if gelap else cls.terang


class Tombol(Button):
    """Button rata (flat) yang warnanya diambil dari Tema."""

    gaya = StringProperty("utama")
    gaya_teks = StringProperty("putih")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.perbarui_warna()

    def on_gaya(self, *args):
        self.perbarui_warna()

    def on_gaya_teks(self, *args):
        self.perbarui_warna()

    def perbarui_warna(self):
        self.background_color = Tema.warna[self.gaya]
        self.color = Tema.warna[self.gaya_teks]


class Kartu(BoxLayout):
    """Panel dengan latar warna dan sudut membulat."""

    def __init__(self, warna=None, radius=12, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self.instr_warna = Color(rgba=warna or Tema.warna["kartu"])
            self.bg = RoundedRectangle(pos=self.pos, size=self.size,
                                       radius=[radius])
        self.bind(pos=self.perbarui_bg, size=self.perbarui_bg)

    def perbarui_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


class Navigasi(BoxLayout):
    """Bar navigasi bawah, dipakai di semua layar."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 58
        self.padding = [4, 4]
        self.spacing = 4
        menu = [("Beranda", "home"), ("Kegiatan", "kegiatan"),
                ("Timer", "timer"), ("Tasbih", "tasbih"),
                ("Lainnya", "pengaturan")]
        for judul, nama_screen in menu:
            btn = Tombol(text=judul, font_size=12, gaya="nav",
                         gaya_teks="teks")
            btn.bind(on_release=lambda b, s=nama_screen: self.pindah(s))
            self.add_widget(btn)

    def pindah(self, nama):
        sm = App.get_running_app().root
        if sm.current != nama:
            sm.current = nama


class BarisTimeline(Kartu):
    """Satu baris timeline di Beranda: jam + nama kegiatan."""

    def __init__(self, jam, nama, warna, **kwargs):
        super().__init__(warna=warna, **kwargs)
        self.size_hint_y = None
        self.height = 46
        self.padding = [14, 0]
        self.add_widget(Label(text=jam, size_hint_x=0.25, bold=True,
                              color=Tema.warna["teks"]))
        self.add_widget(Label(text=nama, size_hint_x=0.75,
                              color=Tema.warna["teks"]))


class BarisCeklis(Kartu):
    """Satu baris ceklis: tombol centang + nama + tombol hapus."""

    def __init__(self, data, selesai, layar, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 48
        self.padding = [10, 4]
        self.item_id = data["id"]
        self.layar = layar
        self.selesai = selesai
        self.instr_warna.rgba = self.warna_baris()

        self.tombol = Tombol(text="[x]" if selesai else "[ ]",
                             gaya="utama" if selesai else "netral",
                             gaya_teks="putih" if selesai else "teks",
                             size_hint_x=0.14, font_size=15)
        self.tombol.bind(on_release=self.tekan)
        self.add_widget(self.tombol)

        self.add_widget(Label(text=data["nama"], size_hint_x=0.68,
                              font_size=16, color=Tema.warna["teks"]))

        hapus = Tombol(text="Hapus", gaya="netral", gaya_teks="teks_pudar",
                       size_hint_x=0.18, font_size=12)
        hapus.bind(on_release=lambda b: self.hapus())
        self.add_widget(hapus)

    def warna_baris(self):
        return (Tema.warna["utama_muda"] if self.selesai
                else Tema.warna["netral"])

    def tekan(self, *_):
        db.toggle_ceklis(self.item_id, datetime.date.today().isoformat())
        self.layar.muat_ceklis()

    def hapus(self):
        db.hapus_item_ceklis(self.item_id)
        self.layar.muat_ceklis()


class PopupCeklis(Popup):
    """Form kecil melayang untuk menambah item ceklis."""

    def __init__(self, layar, **kwargs):
        super().__init__(**kwargs)
        self.layar = layar
        self.title = "Tambah Item Ceklis"
        self.size_hint = (0.9, None)
        self.height = 210
        kotak = BoxLayout(orientation="vertical", padding=15, spacing=10)
        kotak.add_widget(Label(text="Nama item ceklis:",
                               size_hint_y=None, height=26))
        self.input = TextInput(hint_text="contoh: Sholat dhuha",
                               multiline=False, size_hint_y=None, height=44)
        kotak.add_widget(self.input)
        tombol = Tombol(text="Simpan", size_hint_y=None, height=48)
        tombol.bind(on_release=self.simpan)
        kotak.add_widget(tombol)
        self.content = kotak

    def simpan(self, *_):
        nama = self.input.text.strip()
        if nama:
            db.tambah_item_ceklis(nama)
        self.dismiss()
        self.layar.muat_ceklis()


class PopupAlarm(Popup):
    """Jendela alarm yang muncul saat waktu ibadah/kegiatan mendekat."""

    def __init__(self, judul, pesan, **kwargs):
        super().__init__(**kwargs)
        self.title = judul
        self.size_hint = (0.85, None)
        self.height = 230
        kotak = BoxLayout(orientation="vertical", padding=18, spacing=12)
        kotak.add_widget(Label(text=pesan, font_size=18))
        tombol = Tombol(text="Tutup", size_hint_y=None, height=48)
        tombol.bind(on_release=lambda *a: self.dismiss())
        kotak.add_widget(tombol)
        self.content = kotak
        Clock.schedule_once(lambda dt: self.dismiss(), 45)


class HomeScreen(Screen):
    tanggal = StringProperty("")
    countdown = StringProperty("Memuat jadwal...")
    teks_streak = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.jadwal = None
        self.jam_event = None
        self.sedang_memuat = False
        self.kegiatan_hari_ini = []
        self.notif_terkirim = set()

    def on_enter(self):
        hari = datetime.date.today()
        self.tanggal = (f"{HARI[hari.weekday()]}, {hari.day} "
                        f"{BULAN[hari.month - 1]} {hari.year}")

        kota = db.ambil_pengaturan("kota", KOTA_DEFAULT)
        lat = db.ambil_pengaturan("lat")
        lon = db.ambil_pengaturan("lon")
        kunci = ("auto:" + kota) if lat else kota
        cache = db.ambil_jadwal(kunci, hari.isoformat())
        if cache:
            self.jadwal = cache
        elif not self.sedang_memuat:
            self.sedang_memuat = True
            self.countdown = "Memuat jadwal..."
            threading.Thread(target=self.ambil_dari_api,
                             args=(kota, lat, lon), daemon=True).start()

        self.muat_timeline()
        self.muat_ceklis()
        self.mulai_countdown()

    def on_leave(self):
        if self.jam_event:
            self.jam_event.cancel()
            self.jam_event = None

    def ambil_dari_api(self, kota, lat, lon):
        jadwal, pesan_error = None, ""
        try:
            if lat and lon:
                jadwal = prayertimes.ambil_jadwal_koordinat(lat, lon)
            else:
                jadwal = prayertimes.ambil_jadwal(kota)
        except Exception as e:
            pesan_error = f"{type(e).__name__}: {e}"
        Clock.schedule_once(lambda dt: self.jadwal_tiba(jadwal, pesan_error))

    def jadwal_tiba(self, jadwal, pesan_error=""):
        self.sedang_memuat = False
        if jadwal:
            kota = db.ambil_pengaturan("kota", KOTA_DEFAULT)
            lat = db.ambil_pengaturan("lat")
            kunci = ("auto:" + kota) if lat else kota
            db.simpan_jadwal(kunci, datetime.date.today().isoformat(), jadwal)
            self.jadwal = jadwal
            App.get_running_app().jadwal = jadwal
            self.muat_timeline()
            self.perbarui_countdown()
        else:
            self.countdown = f"Gagal: {pesan_error}"

    def mulai_countdown(self):
        if self.jam_event:
            return
        self.perbarui_countdown()
        self.jam_event = Clock.schedule_interval(self.perbarui_countdown, 30)

    def perbarui_countdown(self, *args):
        self.cek_notif_kegiatan()
        if not self.jadwal:
            return
        nama, target, besok = self.waktu_berikutnya()
        selisih = int((target - datetime.datetime.now()).total_seconds())
        if selisih < 0:
            selisih = 0
        j = selisih // 3600
        m = (selisih % 3600) // 60
        keterangan = " (besok)" if besok else ""
        self.countdown = f"Menuju {nama}{keterangan} - {j}j {m:02d}m"

    def waktu_berikutnya(self):
        sekarang = datetime.datetime.now()
        for nama, jam in self.jadwal:
            j, m = map(int, jam.split(":"))
            target = sekarang.replace(hour=j, minute=m, second=0, microsecond=0)
            if target > sekarang:
                return nama, target, False
        nama, jam = self.jadwal[0]
        j, m = map(int, jam.split(":"))
        target = sekarang.replace(hour=j, minute=m, second=0, microsecond=0)
        return nama, target + datetime.timedelta(days=1), True

    def cek_notif_kegiatan(self):
        sekarang = datetime.datetime.now().strftime("%H:%M")
        for id_k, nama, jam in self.kegiatan_hari_ini:
            if jam == sekarang and id_k not in self.notif_terkirim:
                self.notif_terkirim.add(id_k)
                kirim_notif("IbadahKu", f"Waktunya: {nama}")

    def muat_timeline(self):
        daftar = self.ids.timeline
        daftar.clear_widgets()
        item = []
        self.kegiatan_hari_ini = []
        if self.jadwal:
            item = [(jam, nama, Tema.warna["utama_muda"])
                    for nama, jam in self.jadwal]
        for k in db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()]):
            item.append((k["jam"], k["nama"], Tema.warna["netral"]))
            self.kegiatan_hari_ini.append((k["id"], k["nama"], k["jam"]))
        item.sort(key=lambda x: x[0])
        for jam, nama, warna in item:
            daftar.add_widget(BarisTimeline(jam, nama, warna))

    def muat_ceklis(self):
        grid = self.ids.grid_ceklis
        grid.clear_widgets()
        hari = datetime.date.today().isoformat()
        status = db.status_ceklis(hari)
        selesai = total = 0
        for c in db.semua_ceklis():
            total += 1
            done = status.get(c["id"], False)
            if done:
                selesai += 1
            grid.add_widget(BarisCeklis(c, done, self))
        streak = db.hitung_streak()
        self.teks_streak = (f"Streak: {streak} hari  "
                            f" Selesai hari ini: {selesai}/{total}")

    def buka_popup_ceklis(self):
        PopupCeklis(self).open()


class BarisKegiatan(Kartu):
    """Satu baris kegiatan di layar Kegiatan + tombol hapus."""

    def __init__(self, data, layar, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 64
        self.padding = [14, 8]
        info = BoxLayout(orientation="vertical")
        info.add_widget(Label(text=data["nama"], bold=True, font_size=17,
                              color=Tema.warna["teks"]))
        info.add_widget(Label(
            text=f"{data['jam']}  •  {data['hari']}  •  {data['kategori']}",
            font_size=13, color=Tema.warna["teks_pudar"]))
        self.add_widget(info)
        btn = Tombol(text="Hapus", gaya="netral", gaya_teks="teks_pudar",
                     size_hint_x=0.22, font_size=12)
        btn.bind(on_release=lambda b: self.hapus(data["id"], layar))
        self.add_widget(btn)

    def hapus(self, id_kegiatan, layar):
        db.hapus(id_kegiatan)
        layar.muat_daftar()


class KegiatanScreen(Screen):
    def on_enter(self):
        self.muat_daftar()

    def muat_daftar(self):
        daftar = self.ids.daftar_kegiatan
        daftar.clear_widgets()
        for k in db.semua():
            daftar.add_widget(BarisKegiatan(k, self))


class TambahScreen(Screen):
    def simpan(self):
        nama = self.ids.inp_nama.text.strip()
        jam = self.ids.inp_jam.text.strip()
        if not nama:
            self.ids.lbl_pesan.text = "Nama kegiatan belum diisi"
            return
        cocok = re.fullmatch(r"(\d{1,2}):(\d{2})", jam)
        if not cocok:
            self.ids.lbl_pesan.text = "Format jam: HH:MM (contoh: 06:30)"
            return
        j, m = int(cocok.group(1)), int(cocok.group(2))
        if j > 23 or m > 59:
            self.ids.lbl_pesan.text = "Jam tidak valid (00:00 - 23:59)"
            return
        jam = f"{j:02d}:{m:02d}"
        db.tambah(nama, jam, self.ids.spin_hari.text,
                  self.ids.spin_kategori.text)
        self.ids.inp_nama.text = ""
        self.ids.inp_jam.text = ""
        self.ids.lbl_pesan.text = ""
        self.manager.current = "kegiatan"


class TimerScreen(Screen):
    waktu = StringProperty("15:00")
    status = StringProperty("Pilih durasi lalu tekan Mulai")
    total_hari_ini = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sisa = 0
        self.total = 1
        self.event = None

    def on_enter(self):
        self.perbarui_total()

    def perbarui_total(self):
        self.total_hari_ini = f"Total sesi hari ini: {db.total_timer_hari_ini()} menit"

    def mulai(self):
        if self.event:
            return
        if self.sisa <= 0:
            menit = int(self.ids.spin_durasi.text)
            self.total = menit * 60
            self.sisa = self.total
        self.status = "Sesi berjalan..."
        self.tampilkan()
        self.event = Clock.schedule_interval(self.detik, 1)

    def jeda(self):
        if self.event:
            self.event.cancel()
            self.event = None
            self.status = "Jeda - tekan Mulai untuk lanjut"

    def ulang(self):
        self.jeda()
        self.sisa = 0
        self.waktu = "00:00"
        self.status = "Direset. Pilih durasi lalu Mulai"
        self.ids.progres.value = 0

    def detik(self, dt):
        self.sisa -= 1
        if self.sisa <= 0:
            self.selesai_sesi()
            return
        self.tampilkan()

    def tampilkan(self):
        m = self.sisa // 60
        s = self.sisa % 60
        self.waktu = f"{m:02d}:{s:02d}"
        self.ids.progres.value = 1 - self.sisa / self.total

    def selesai_sesi(self):
        self.jeda()
        self.sisa = 0
        self.waktu = "00:00"
        self.ids.progres.value = 1
        self.status = "Alhamdulillah, sesi selesai!"
        db.catat_timer(self.total // 60)
        self.perbarui_total()
        kirim_notif("IbadahKu", "Sesi ibadah selesai. Alhamdulillah!")


class TasbihScreen(Screen):
    hitungan_label = StringProperty("0")
    progres_label = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hitungan = 0
        self.tercatat = 0

    def on_enter(self):
        hari = datetime.date.today().isoformat()
        self.hitungan = db.ambil_tasbih(hari)
        self.tercatat = self.hitungan
        self.perbarui()

    def on_leave(self):
        self.simpan()

    def simpan(self):
        delta = self.hitungan - self.tercatat
        if delta > 0:
            db.simpan_tasbih(datetime.date.today().isoformat(), delta)
            self.tercatat = self.hitungan

    def tap(self):
        self.hitungan += 1
        teks_target = self.ids.spin_target.text
        if teks_target != "Bebas":
            target = int(teks_target)
            if self.hitungan == target:
                kirim_notif("IbadahKu",
                            f"MasyaAllah, {target}x {self.ids.spin_dzikir.text} selesai!")
        self.perbarui()

    def ulang(self):
        self.hitungan = 0
        self.tercatat = 0
        db.reset_tasbih(datetime.date.today().isoformat())
        self.perbarui()

    def perbarui(self, *args):
        try:
            teks_target = self.ids.spin_target.text
        except AttributeError:
            return
        self.hitungan_label = str(self.hitungan)
        if teks_target == "Bebas":
            self.progres_label = "Mode bebas (tanpa target)"
        else:
            self.progres_label = f"{self.hitungan} / {teks_target}"


class StatistikScreen(Screen):
    def on_enter(self):
        self.muat_statistik()

    def muat_statistik(self):
        grid = self.ids.grid_stat
        grid.clear_widgets()
        hari = datetime.date.today().isoformat()
        awal = (datetime.date.today()
                - datetime.timedelta(days=6)).isoformat()
        streak = db.hitung_streak()
        status = db.status_ceklis(hari)
        selesai = sum(1 for v in status.values() if v)
        aktif = len(db.semua_ceklis())
        menit_hari = db.total_timer_hari_ini()
        tasbih_hari = db.ambil_tasbih(hari)
        menit_minggu, tasbih_minggu, hari_aktif = db.ringkasan_minggu(awal)
        total_menit, total_tasbih = db.total_keseluruhan()
        self.baris(grid, "Streak ceklis", f"{streak} hari beruntun")
        self.baris(grid, "Ceklis hari ini", f"{selesai} dari {aktif} item selesai")
        self.baris(grid, "Timer hari ini", f"{menit_hari} menit")
        self.baris(grid, "Tasbih hari ini", f"{tasbih_hari} kali")
        self.baris(grid, "7 hari terakhir",
                   f"{menit_minggu} menit  •  {tasbih_minggu}x dzikir  •  "
                   f"aktif {hari_aktif} hari")
        self.baris(grid, "Total keseluruhan",
                   f"{total_menit} menit  •  {total_tasbih}x dzikir")

    def baris(self, grid, judul, isi):
        kartu = Kartu(size_hint_y=None, height=72, padding=[16, 8])
        kotak = BoxLayout(orientation="vertical")
        kotak.add_widget(Label(text=judul, font_size=13,
                               color=Tema.warna["teks_pudar"],
                               size_hint_y=None, height=22))
        kotak.add_widget(Label(text=isi, font_size=16, bold=True,
                               color=Tema.warna["teks"]))
        kartu.add_widget(kotak)
        grid.add_widget(kartu)


class DoaScreen(Screen):
    """Bacaan doa harian: satu doa per hari + tombol pindah."""

    judul = StringProperty("")
    arab = StringProperty("")
    latin = StringProperty("")
    arti = StringProperty("")
    nomor = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.indeks = datetime.date.today().timetuple().tm_yday % len(DOA)

    def on_enter(self):
        self.tampilkan()

    def tampilkan(self):
        d = DOA[self.indeks]
        self.judul = d["judul"]
        self.arab = siapkan_arab(d["arab"])
        self.latin = d["latin"]
        self.arti = '"' + d["arti"] + '"'
        self.nomor = f"{self.indeks + 1} / {len(DOA)}"

    def sebelumnya(self):
        self.indeks = (self.indeks - 1) % len(DOA)
        self.tampilkan()

    def berikutnya(self):
        self.indeks = (self.indeks + 1) % len(DOA)
        self.tampilkan()


class KompasKiblat(Widget):
    """Dial kompas + panah merah menunjuk arah kiblat (derajat dari utara)."""

    sudut = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.huruf = {}
        for h, (dx, dy) in [("U", (0, 1)), ("T", (1, 0)),
                            ("S", (0, -1)), ("B", (-1, 0))]:
            l = Label(text=h, font_size=15, bold=True, size=(22, 22),
                      size_hint=(None, None), color=Tema.warna["teks_pudar"])
            self.add_widget(l)
            self.huruf[h] = (l, dx, dy)
        self.bind(pos=self.gambar, size=self.gambar, sudut=self.gambar)

    def gambar(self, *args):
        cx, cy = self.center
        r = min(self.width, self.height) / 2 - 24
        for l, dx, dy in self.huruf.values():
            l.center = (cx + dx * (r + 12), cy + dy * (r + 12))
        self.canvas.clear()
        with self.canvas:
            Color(rgba=Tema.warna["teks_pudar"])
            Line(circle=(cx, cy, r), width=1.5)
            Line(circle=(cx, cy, 3))
            # tanda arah utara
            Line(points=[cx, cy + r - 4, cx, cy + r - 16], width=2)
            # panah arah kiblat
            rad = math.radians(self.sudut)
            ux, uy = cx + (r - 28) * math.sin(rad), cy + (r - 28) * math.cos(rad)
            bx, by = cx - (r - 52) * math.sin(rad), cy - (r - 52) * math.cos(rad)
            Color(rgba=(0.78, 0.26, 0.26, 1))
            Line(points=[bx, by, ux, uy], width=4)
            p1x = ux + 14 * math.sin(rad + 2.5)
            p1y = uy + 14 * math.cos(rad + 2.5)
            p2x = ux + 14 * math.sin(rad - 2.5)
            p2y = uy + 14 * math.cos(rad - 2.5)
            Triangle(points=[ux, uy, p1x, p1y, p2x, p2y])


class KiblatScreen(Screen):
    ARAH = ["Utara", "Timur Laut", "Timur", "Tenggara",
            "Selatan", "Barat Daya", "Barat", "Barat Laut"]

    info = StringProperty("")
    derajat = StringProperty("")
    keterangan = StringProperty("")

    def on_enter(self):
        lat = db.ambil_pengaturan("lat")
        lon = db.ambil_pengaturan("lon")
        if lat and lon:
            lokasi = db.ambil_pengaturan("kota", KOTA_DEFAULT) + " (otomatis)"
            la, lo = float(lat), float(lon)
        else:
            nama = db.ambil_pengaturan("kota", KOTA_DEFAULT)
            lokasi = nama + " (manual)"
            la, lo = prayertimes.KOTA_KOORDINAT.get(
                nama, prayertimes.KOTA_KOORDINAT[KOTA_DEFAULT])
        b = prayertimes.arah_kiblat(la, lo)
        arah = self.ARAH[int((b + 22.5) // 45) % 8]
        self.info = f"Lokasi: {lokasi}"
        self.derajat = f"{b:.0f} derajat"
        self.keterangan = (f"Arah kiblat: {arah} dari utara.\n"
                           "Cara pakai: hadap ke arah UTARA,\n"
                           f"lalu putar {b:.0f} derajat searah jarum jam.")
        self.ids.kompas.sudut = b


class PengaturanScreen(Screen):
    def on_enter(self):
        self._sedang_muat = True
        spin = self.ids.spin_kota
        if not spin.values:
            spin.values = DAFTAR_KOTA
        spin.text = db.ambil_pengaturan("kota", KOTA_DEFAULT)
        self.ids.sw_alarm.active = db.ambil_pengaturan("alarm_aktif", "0") == "1"
        self.ids.spin_alarm_menit.text = db.ambil_pengaturan("alarm_menit", "10")
        if db.ambil_pengaturan("lat"):
            self.ids.lbl_lokasi.text = ("Mode otomatis aktif: "
                                        + db.ambil_pengaturan("kota", KOTA_DEFAULT))
        else:
            self.ids.lbl_lokasi.text = "Mode manual (kota dipilih sendiri)"
        self.ids.lbl_status.text = ""
        self._sedang_muat = False

    # ----- alarm -----

    def ubah_alarm(self, saklar, aktif):
        if getattr(self, "_sedang_muat", False):
            return
        db.simpan_pengaturan("alarm_aktif", "1" if aktif else "0")

    def pilih_menit(self):
        if getattr(self, "_sedang_muat", False):
            return
        db.simpan_pengaturan("alarm_menit", self.ids.spin_alarm_menit.text)

    # ----- lokasi -----

    def simpan_kota(self):
        kota = self.ids.spin_kota.text
        db.simpan_pengaturan("kota", kota)
        db.simpan_pengaturan("lat", "")   # manual: hapus koordinat otomatis
        db.simpan_pengaturan("lon", "")
        self.ids.lbl_lokasi.text = "Mode manual (kota dipilih sendiri)"
        self.ids.lbl_status.text = f"Kota manual tersimpan: {kota}"

    def deteksi_lokasi(self):
        self.ids.lbl_lokasi.text = "Mendeteksi lokasi (butuh internet)..."
        threading.Thread(target=self._deteksi, daemon=True).start()

    def _deteksi(self):
        """Berjalan di thread kedua - jaringan tidak boleh di thread utama."""
        try:
            kota, lat, lon = prayertimes.deteksi_lokasi()
        except Exception as e:
            pesan = f"Gagal mendeteksi: {type(e).__name__}"
            Clock.schedule_once(lambda dt: self._set_lokasi(pesan))
            return
        db.simpan_pengaturan("kota", kota)
        db.simpan_pengaturan("lat", str(lat))
        db.simpan_pengaturan("lon", str(lon))
        info = (f"Mode otomatis aktif: {kota}\n"
                "Buka ulang Beranda untuk memuat jadwalnya")
        Clock.schedule_once(lambda dt: self._set_lokasi(info))

    def _set_lokasi(self, teks):
        self.ids.lbl_lokasi.text = teks

    # ----- mode gelap -----

    def ubah_mode(self, saklar, aktif):
        if getattr(self, "_sedang_muat", False):
            return
        db.simpan_pengaturan("mode_gelap", "1" if aktif else "0")
        self.ids.lbl_status.text = ("Tersimpan! Buka ulang aplikasi "
                                    "untuk melihat temanya")


class IbadahKuApp(App):
    title = "IbadahKu"

    warna_utama = ListProperty((0.13, 0.45, 0.36, 1))
    warna_teks = ListProperty((0.13, 0.15, 0.14, 1))
    warna_pudar = ListProperty((0.45, 0.48, 0.46, 1))
    font_arab = "data/fonts/Roboto-Regular.ttf"

    def build(self):
        db.buat_tabel()
        Tema.muat()
        Window.clearcolor = Tema.warna["latar"]
        self.warna_utama = Tema.warna["utama"]
        self.warna_teks = Tema.warna["teks"]
        self.warna_pudar = Tema.warna["teks_pudar"]
        self.font_arab = cari_font_arab()

        # alarm: jadwal & agenda
        self.jadwal = _baca_jadwal_cache()
        self.alarm_terkirim = set()
        try:
            self.bunyi = SoundLoader.load(buat_file_bunyi())
        except Exception:
            self.bunyi = None
        Clock.schedule_interval(self.cek_alarm, 20)

        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(KegiatanScreen(name="kegiatan"))
        sm.add_widget(TambahScreen(name="tambah"))
        sm.add_widget(TimerScreen(name="timer"))
        sm.add_widget(TasbihScreen(name="tasbih"))
        sm.add_widget(StatistikScreen(name="statistik"))
        sm.add_widget(DoaScreen(name="doa"))
        sm.add_widget(KiblatScreen(name="kiblat"))
        sm.add_widget(PengaturanScreen(name="pengaturan"))
        return sm

    def cek_alarm(self, *args):
        """Tiap 20 detik: cek jadwal sholat + kegiatan, alarm H-X menit."""
        if db.ambil_pengaturan("alarm_aktif", "0") != "1":
            return
        if not self.jadwal:
            self.jadwal = _baca_jadwal_cache() or []
        if not self.jadwal:
            return
        offset = int(db.ambil_pengaturan("alarm_menit", "10"))
        sekarang = datetime.datetime.now()
        agenda = list(self.jadwal)
        for k in db.kegiatan_hari_ini(HARI[sekarang.weekday()]):
            agenda.append((k["nama"], k["jam"]))
        for nama, jam in agenda:
            h, m = map(int, jam.split(":"))
            waktunya = sekarang.replace(hour=h, minute=m, second=0,
                                        microsecond=0)
            pengingat = waktunya - datetime.timedelta(minutes=offset)
            kunci = f"{nama}@{jam}"
            if (pengingat <= sekarang < waktunya
                    and kunci not in self.alarm_terkirim):
                self.alarm_terkirim.add(kunci)
                pesan = f"{nama} pukul {jam} - sekitar {offset} menit lagi"
                kirim_notif("Pengingat IbadahKu", pesan)
                if self.bunyi:
                    try:
                        self.bunyi.play()
                    except Exception:
                        pass
                PopupAlarm("Segera Waktunya!", pesan).open()


if __name__ == "__main__":
    IbadahKuApp().run()