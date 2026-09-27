# pyright: reportMissingImports=false

import datetime
import math
import os
import re
import random
import struct
import threading
import wave

from kivy.clock import Clock
from kivy.config import Config
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Line, RoundedRectangle, Triangle, Rectangle, Ellipse
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.utils import platform, get_color_from_hex

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDFlatButton, MDRaisedButton

import database as db
import prayertimes
from doa import DOA
try:
    import achievements
except ImportError:
    class MockAchievements:
        def evaluasi(self): return []
        def semua_dengan_status(self): return []
    achievements = MockAchievements()

if platform != 'android' and platform != 'ios':
    Config.set("graphics", "width", "400")
    Config.set("graphics", "height", "700")

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Ahad"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

PALET = {
    "teal": get_color_from_hex("#127063"),
    "teal_soft": get_color_from_hex("#DCEAE4"),
    "emas": get_color_from_hex("#C99A3E"),
    "emas_soft": get_color_from_hex("#F1E2BB"),
    "kertas": get_color_from_hex("#F7F1E1"),
    "kertas_dim": get_color_from_hex("#EEE4CC"),
    "permukaan": get_color_from_hex("#FFFCF4"),
    "malam": get_color_from_hex("#101A18"),
    "malam_kartu": get_color_from_hex("#17251F"),
    "ivory": get_color_from_hex("#EFE7D3"),
    "tinta": get_color_from_hex("#16302C"),
}

KOTA_DEFAULT = "Jakarta"
DAFTAR_KOTA = [
    "Jakarta", "Bandung", "Bekasi", "Bogor", "Tangerang", "Depok",
    "Semarang", "Yogyakarta", "Surabaya", "Malang",
    "Medan", "Palembang", "Makassar", "Denpasar",
]

AYAT_HARIAN = [
    {"surah": "Al-Baqarah 2:286", "arab": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "arti": "Allah tidak membebani seseorang melainkan sesuai dengan kesanggupannya."},
    {"surah": "Al-Insyirah 94:6", "arab": "إِنَّ مَعَ الْعُسْرِ يُسْرًا", "arti": "Sesungguhnya bersama kesulitan ada kemudahan."},
    {"surah": "Ali Imran 3:139", "arab": "وَلَا تَهِنُوا وَلَا تَحْزَنُوا وَأَنتُمُ الْأَعْلَوْنَ", "arti": "Janganlah kamu merasa lemah dan jangan pula bersedih, padahal kamu orang-orang yang paling tinggi (derajatnya)."},
    {"surah": "Ath-Thalaq 65:3", "arab": "وَمَن يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ", "arti": "Barangsiapa bertawakal kepada Allah, niscaya Allah akan mencukupkan keperluannya."},
    {"surah": "Al-Baqarah 2:152", "arab": "فَاذْكُرُونِي أَذْكُرْكُمْ", "arti": "Maka ingatlah kepada-Ku, niscaya Aku akan mengingat kalian."},
    {"surah": "Ar-Ra'd 13:28", "arab": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "arti": "Ingatlah, hanya dengan mengingat Allah hati menjadi tenteram."},
    {"surah": "Al-Ankabut 29:69", "arab": "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا", "arti": "Orang-orang yang berjihad di jalan Kami, sungguh akan Kami tunjukkan jalan-jalan Kami."},
    {"surah": "Ibrahim 14:7", "arab": "لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ", "arti": "Jika kamu bersyukur, niscaya Aku akan menambah (nikmat) kepadamu."},
    {"surah": "Al-Hasyr 59:18", "arab": "يَا أَيُّهَا الَّذِينَ آمَنُوا اتَّقُوا اللَّهَ وَلْتَنظُرْ نَفْسٌ مَّا قَدَّمَتْ لِغَدٍ", "arti": "Wahai orang-orang yang beriman, bertakwalah kepada Allah dan hendaklah setiap jiwa memperhatikan apa yang telah diperbuatnya untuk hari esok."},
    {"surah": "Taha 20:114", "arab": "وَقُل رَّبِّ زِدْنِي عِلْمًا", "arti": "Dan katakanlah, 'Ya Tuhanku, tambahkanlah ilmu kepadaku.'"},
]

try:
    from plyer import notification, vibrator
except ImportError:
    notification = None
    vibrator = None

# Arabic text support.
# Kivy's SDL2 text provider receives the already-shaped visual string.
# The bundled Noto Naskh Arabic font supplies the Arabic glyphs/diacritics.
try:
    import unicodedata
    import arabic_reshaper
    from bidi.algorithm import get_display

    def siapkan_arab(teks):
        if not teks:
            return ""
        teks = unicodedata.normalize("NFC", str(teks))
        # Remove invisible bidi/control marks that can confuse manual shaping.
        teks = "".join(
            ch for ch in teks
            if unicodedata.category(ch) != "Cf"
            or ch in "\n\r\t"
        )
        shaped = arabic_reshaper.reshape(teks)
        return get_display(shaped, base_dir="R")
except ImportError:
    def siapkan_arab(teks):
        return str(teks or "")

def kirim_notif(judul, pesan):
    if notification is None:
        return
    try:
        notification.notify(title=judul, message=pesan,
                            app_name="IbadahKu", timeout=10)
    except Exception:
        pass

def get_haptic():
    if vibrator:
        try:
            vibrator.vibrate(0.05)
        except Exception:
            pass

def cari_font_arab():
    """Return a bundled Arabic-capable font, with safe Windows fallbacks."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(base_dir, "fonts")
    bundled_fonts = (
        "NotoNaskhArabic-Regular.ttf",
        "NotoNaskhArabicUI-Regular.ttf",
        "NotoSansArabic-Regular.ttf",
        "DejaVuSans.ttf",
    )
    for nama in bundled_fonts:
        path = os.path.join(font_dir, nama)
        if os.path.isfile(path):
            return path

    # Fallback only if a user runs an old copy without bundled fonts.
    for path in (
        r"C:\Windows\Fonts\NotoNaskhArabic-Regular.ttf",
        r"C:\Windows\Fonts\NotoNaskhArabicUI-Regular.ttf",
        r"C:\Windows\Fonts\NotoSansArabic-Regular.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "Font Arab tidak ditemukan. Pastikan fonts/NotoNaskhArabic-Regular.ttf ada."
    )

def buat_file_bunyi(nama="beep.wav"):
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

class Navigasi(MDBoxLayout):
    layar_aktif = StringProperty("home")

    def pindah(self, nama):
        sm = MDApp.get_running_app().root
        if sm.current != nama:
            sm.current = nama

class BarisTimeline(MDCard):
    jam = StringProperty()
    nama = StringProperty()
    is_jadwal = BooleanProperty(False)


class BarisCeklisKegiatan(MDCard):
    data = ObjectProperty()
    selesai = BooleanProperty(False)
    layar = ObjectProperty()

    def on_release(self):
        if not self.data or not self.layar:
            return
        tanggal = datetime.date.today().isoformat()
        db.set_kegiatan_selesai(self.data["id"], tanggal, not self.selesai)
        self.layar.muat_ceklis()

    def hapus(self):
        if self.data and self.layar:
            self.layar.hapus_kegiatan(self.data["id"])


class BarisCeklis(MDCard):
    data = ObjectProperty()
    selesai = BooleanProperty(False)
    layar = ObjectProperty()
    
    def on_release(self):
        tanggal = datetime.date.today().isoformat()
        db.set_ceklis(self.data['id'], tanggal, not self.selesai)
        self.layar.muat_ceklis()
        
    def hapus(self):
        app = MDApp.get_running_app()
        self.dialog = MDDialog(
            title="Hapus item?",
            text="Item ini akan disembunyikan dari daftar.",
            buttons=[
                MDFlatButton(
                    text="BATAL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="HAPUS",
                    text_color=app.theme_cls.error_color,
                    on_release=lambda x: self._proses_hapus()
                ),
            ],
        )
        self.dialog.open()
        
    def _proses_hapus(self):
        db.hapus_item_ceklis(self.data['id'])
        self.dialog.dismiss()
        self.layar.muat_ceklis()

class PopupCeklis:
    def __init__(self, layar):
        self.layar = layar
        from kivymd.uix.textfield import MDTextField
        self.input = MDTextField(hint_text="contoh: Sholat dhuha")
        self.dialog = MDDialog(
            title="Tambah Item Ceklis",
            type="custom",
            content_cls=self.input,
            buttons=[
                MDFlatButton(
                    text="BATAL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="SIMPAN",
                    theme_text_color="Custom",
                    text_color=MDApp.get_running_app().theme_cls.primary_color,
                    on_release=lambda x: self.simpan()
                ),
            ],
        )
        
    def open(self):
        self.dialog.open()
        
    def simpan(self):
        nama = self.input.text.strip()
        if nama:
            db.tambah_item_ceklis(nama)
        self.dialog.dismiss()
        self.layar.muat_ceklis()

class PopupAlarm:
    def __init__(self, judul, pesan):
        self.dialog = MDDialog(
            title=judul,
            text=pesan,
            buttons=[
                MDFlatButton(
                    text="TUTUP",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ],
        )
        Clock.schedule_once(lambda dt: self.dialog.dismiss(), 45)
        
    def open(self):
        self.dialog.open()

class SplashScreen(MDScreen):
    def on_enter(self):
        Clock.schedule_once(self.pindah, 2.5)
        
    def pindah(self, dt):
        self.manager.current = "home"

class HomeScreen(MDScreen):
    tanggal = StringProperty("")
    tanggal_hijri = StringProperty("")
    countdown = StringProperty("Memuat jadwal...")
    teks_streak = StringProperty("")
    ringkasan = StringProperty("")
    progres_hari = StringProperty("")
    kutipan = StringProperty("")
    ayat_hari = StringProperty("")
    surah_hari = StringProperty("")
    arti_hari = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.jadwal = None
        self.jam_event = None
        self.sedang_memuat = False
        self.kegiatan_hari_ini = []
        self.notif_terkirim = set()
        self._tanggal_aktif = None

    def on_enter(self):
        hari = datetime.date.today()
        self._tanggal_aktif = hari.isoformat()
        self.tanggal = f"{HARI[hari.weekday()]}, {hari.day} {BULAN[hari.month - 1]} {hari.year}"
        
        # simple random for the day
        idx = hari.toordinal() % len(AYAT_HARIAN)
        ayat = AYAT_HARIAN[idx]
        self.ayat_hari = siapkan_arab(ayat["arab"])
        self.surah_hari = ayat["surah"]
        self.arti_hari = ayat["arti"]
        
        # simple pseudo hijri
        y, m, d = hari.year, hari.month, hari.day
        jd = int((1461 * (y + 4800 + int((m - 14) / 12))) / 4) + int((367 * (m - 2 - 12 * (int((m - 14) / 12)))) / 12) - int((3 * (int((y + 4900 + int((m - 14) / 12)) / 100))) / 4) + d - 32075
        l = jd - 1948440 + 10632
        n = int((l - 1) / 10631)
        l = l - 10631 * n + 354
        j = (int((10985 - l) / 5316)) * (int((50 * l) / 17719)) + (int(l / 5670)) * (int((43 * l) / 15238))
        l = l - (int((30 - j) / 15)) * (int((17719 * j) / 50)) - (int(j / 16)) * (int((15238 * j) / 43)) + 29
        hm = int((24 * l) / 709)
        hd = l - int((709 * hm) / 24)
        hy = 30 * n + j - 30
        bulan_hijri = ["Muharram", "Safar", "Rabiul Awwal", "Rabiul Akhir", "Jumadil Awwal", "Jumadil Akhir", "Rajab", "Sya'ban", "Ramadhan", "Syawal", "Dzulqa'dah", "Dzulhijjah"]
        try:
            self.tanggal_hijri = f"{hd} {bulan_hijri[hm-1]} {hy} H"
        except:
            self.tanggal_hijri = ""

        # kutipan logic
        kutipan_list = [
            "Sedikit tetapi rutin lebih baik daripada banyak lalu terhenti.",
            "Jadikan hari ini lebih dekat kepada Allah daripada kemarin.",
            "Istirahat boleh, menyerah jangan. Pelan-pelan tetap maju.",
            "Ilmu, doa, dan amal kecil yang konsisten punya nilai besar.",
            "Saat hati tenang, syukur terasa lebih mudah.",
            "Mulai dari satu kebaikan hari ini.",
            "Semoga langkah kecilmu hari ini menjadi bekal yang baik.",
        ]
        self.kutipan = kutipan_list[hari.toordinal() % len(kutipan_list)]

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
            threading.Thread(target=self.ambil_dari_api, args=(kota, lat, lon), daemon=True).start()

        self.muat_timeline()
        self.muat_ceklis()
        self.mulai_countdown()
        
        try:
            badges = achievements.evaluasi()
            for b in badges:
                kirim_notif("Pencapaian Baru!", f"Kamu mendapatkan badge: {b.get('judul', b.get('nama', b.get('id', 'Badge')))}")
        except Exception:
            pass

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
            MDApp.get_running_app().jadwal = jadwal
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
        hari_ini = datetime.date.today().isoformat()
        if self._tanggal_aktif and hari_ini != self._tanggal_aktif:
            self.on_enter()
            return
            
        self.cek_notif_kegiatan()
        if not self.jadwal:
            self.ringkasan = "Jadwal belum tersedia."
            return
        nama, target, besok = self.waktu_berikutnya()
        selisih = int((target - datetime.datetime.now()).total_seconds())
        if selisih < 0:
            selisih = 0
        j = selisih // 3600
        m = (selisih % 3600) // 60
        keterangan = " (besok)" if besok else ""
        self.countdown = f"Menuju {nama}{keterangan} - {j}j {m:02d}m"
        self.ringkasan = f"Waktu berikutnya: {nama} • {target.strftime('%H:%M')}"

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
            kunci = f"kegiatan:{id_k}:{datetime.date.today().isoformat()}"
            if jam == sekarang and kunci not in self.notif_terkirim:
                self.notif_terkirim.add(kunci)
                kirim_notif("IbadahKu", f"Waktunya: {nama}")

    def muat_timeline(self):
        daftar = self.ids.timeline
        daftar.clear_widgets()
        item = []
        self.kegiatan_hari_ini = []
        if self.jadwal:
            item = [(jam, nama, True) for nama, jam in self.jadwal]
        for k in db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()]):
            item.append((k["jam"], k["nama"], False))
            self.kegiatan_hari_ini.append((k["id"], k["nama"], k["jam"]))
        item.sort(key=lambda x: x[0])
        for jam, nama, is_jadwal in item:
            daftar.add_widget(BarisTimeline(jam=jam, nama=nama, is_jadwal=is_jadwal))

    def muat_ceklis(self):
        grid = self.ids.grid_ceklis
        grid.clear_widgets()
        hari = datetime.date.today().isoformat()
        status = db.status_ceklis(hari)
        status_kegiatan = db.status_kegiatan(hari)
        selesai = total = 0

        for c in db.semua_ceklis():
            total += 1
            done = status.get(c["id"], False)
            selesai += int(done)
            grid.add_widget(BarisCeklis(data=c, selesai=done, layar=self))

        # Jadwal kegiatan pribadi ikut menjadi checklist harian.
        for k in db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()]):
            total += 1
            done = status_kegiatan.get(k["id"], False)
            selesai += int(done)
            grid.add_widget(BarisCeklisKegiatan(data=k, selesai=done, layar=self))

        streak = db.hitung_streak()
        persen = int((selesai / total) * 100) if total else 0
        kobar = "\U0001F525 " if streak > 0 else ""
        self.teks_streak = f"{selesai} dari {total} selesai  •  {kobar}streak {streak} hari"
        self.progres_hari = f"{persen}% hari ini"
        self.ids.bar_progress.value = persen

    def hapus_kegiatan(self, kegiatan_id):
        db.hapus(kegiatan_id)
        self.muat_timeline()
        self.muat_ceklis()

    def buka_popup_ceklis(self):
        PopupCeklis(self).open()

    def selesaikan_semua(self):
        tanggal = datetime.date.today().isoformat()
        db.set_semua_ceklis(tanggal, True)
        for k in db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()]):
            db.set_kegiatan_selesai(k["id"], tanggal, True)
        self.muat_ceklis()

    def reset_ceklis_hari_ini(self):
        tanggal = datetime.date.today().isoformat()
        db.set_semua_ceklis(tanggal, False)
        for k in db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()]):
            db.set_kegiatan_selesai(k["id"], tanggal, False)
        self.muat_ceklis()

class BarisKegiatan(MDCard):
    data = ObjectProperty()
    layar = ObjectProperty()
    
    def hapus(self):
        app = MDApp.get_running_app()
        self.dialog = MDDialog(
            title="Hapus kegiatan?",
            text="Kegiatan akan dihapus permanen.",
            buttons=[
                MDFlatButton(
                    text="BATAL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="HAPUS",
                    text_color=app.theme_cls.error_color,
                    on_release=lambda x: self._proses_hapus()
                ),
            ],
        )
        self.dialog.open()
        
    def _proses_hapus(self):
        db.hapus(self.data['id'])
        self.dialog.dismiss()
        self.layar.muat_daftar()

class KegiatanScreen(MDScreen):
    def on_enter(self):
        self.muat_daftar()

    def muat_daftar(self):
        daftar = self.ids.daftar_kegiatan
        daftar.clear_widgets()
        for k in db.semua():
            daftar.add_widget(BarisKegiatan(data=k, layar=self))

class TambahScreen(MDScreen):
    def on_enter(self):
        self._init_menus()
        
    def _init_menus(self):
        hari_items = [{"viewclass": "OneLineListItem", "text": h, "on_release": lambda x=h: self.set_hari(x)} for h in ["Setiap hari", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Ahad"]]
        self.menu_hari = MDDropdownMenu(caller=self.ids.btn_hari, items=hari_items, width_mult=4)
        
        kat_items = [{"viewclass": "OneLineListItem", "text": k, "on_release": lambda x=k: self.set_kat(x)} for k in ["Ibadah", "Belajar", "Lainnya"]]
        self.menu_kategori = MDDropdownMenu(caller=self.ids.btn_kategori, items=kat_items, width_mult=4)

    def set_hari(self, text):
        self.ids.btn_hari.text = text
        self.menu_hari.dismiss()
        
    def set_kat(self, text):
        self.ids.btn_kategori.text = text
        self.menu_kategori.dismiss()

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
        db.tambah(nama, jam, self.ids.btn_hari.text, self.ids.btn_kategori.text)
        self.ids.inp_nama.text = ""
        self.ids.inp_jam.text = ""
        self.ids.lbl_pesan.text = ""
        self.manager.current = "kegiatan"

class CircularProgress(Widget):
    value = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_canvas, size=self.update_canvas, value=self.update_canvas)
        
    def update_canvas(self, *args):
        self.canvas.clear()
        radius = max(1, min(self.width, self.height) / 2 - 10)
        with self.canvas:
            # Always show the neutral ring.
            Color(0.8, 0.8, 0.8, 0.30)
            Line(circle=(self.center_x, self.center_y, radius), width=8)
            # Do not draw a 0-degree arc: SDL/Kivy can render it as a tiny dot.
            value = max(0.0, min(1.0, float(self.value)))
            if value > 0.001:
                app = MDApp.get_running_app()
                Color(rgba=app.theme_cls.primary_color)
                end = 360 if value >= 0.999 else 360 * value
                Line(circle=(self.center_x, self.center_y, radius, 0, end), width=8)

class TimerScreen(MDScreen):
    waktu = StringProperty("15:00")
    status = StringProperty("Pilih durasi lalu tekan Mulai")
    total_hari_ini = StringProperty("")
    durasi_menit = NumericProperty(15)
    progress = NumericProperty(0.0)
    berjalan = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sisa = 15 * 60
        self.total = 15 * 60
        self.event = None
        self.menu = None

    def on_enter(self):
        if not self.menu:
            items = [{"viewclass": "OneLineListItem", "text": str(d), "on_release": lambda x=d: self.set_durasi(x)} for d in [1, 5, 10, 15, 20, 30, 45, 60]]
            self.menu = MDDropdownMenu(caller=self.ids.btn_durasi, items=items, width_mult=2)
            
        self.perbarui_total()
        if self.sisa <= 0:
            self.reset_tampilan_durasi()
            
    def set_durasi(self, menit):
        self.durasi_menit = int(menit)
        self.ids.btn_durasi.text = f"{menit} menit"
        self.menu.dismiss()
        if self.event is None:
            self.reset_tampilan_durasi()

    def reset_tampilan_durasi(self, *args):
        menit = self.durasi_menit
        self.jeda()
        self.total = max(1, menit * 60)
        self.sisa = self.total
        self.berjalan = False
        self.progress = 0.0
        self.tampilkan()
        self.status = f"Siap fokus selama {menit} menit"

    def perbarui_total(self):
        self.total_hari_ini = f"Total sesi hari ini: {db.total_timer_hari_ini()} menit"

    def mulai(self):
        if self.event is not None:
            return
        if self.sisa <= 0:
            self.total = max(1, int(self.durasi_menit) * 60)
            self.sisa = self.total
        self.status = "Sesi berjalan..."
        self.tampilkan()
        self.berjalan = True
        self.event = Clock.schedule_interval(self.detik, 1)

    def jeda(self):
        if self.event is not None:
            self.event.cancel()
            self.event = None
        self.berjalan = False
        if self.sisa > 0:
            self.status = "Jeda - tekan Mulai untuk lanjut"

    def ulang(self):
        self.reset_tampilan_durasi()

    def detik(self, dt):
        self.sisa -= 1
        if self.sisa <= 0:
            self.selesai_sesi()
            return
        self.tampilkan()

    def tampilkan(self):
        total = max(1, int(self.total))
        sisa = max(0, int(self.sisa))
        m = sisa // 60
        s = sisa % 60
        self.waktu = f"{m:02d}:{s:02d}"
        self.progress = min(1.0, max(0.0, 1 - (sisa / total)))
        if "progres" in self.ids:
            self.ids.progres.value = self.progress

    def on_leave(self, *args):
        if self.event is not None:
            self.event.cancel()
            self.event = None
        self.berjalan = False

    def selesai_sesi(self):
        self.jeda()
        self.sisa = 0
        self.waktu = "00:00"
        self.progress = 1.0
        self.ids.progres.value = self.progress
        self.status = "Alhamdulillah, sesi selesai!"
        db.catat_timer(self.total // 60)
        self.perbarui_total()
        kirim_notif("IbadahKu", "Sesi ibadah selesai. Alhamdulillah!")

class TasbihCircleButton(Widget):
    """Lingkaran tasbih yang menangani touch secara langsung.

    Tidak memakai ButtonBehavior agar tidak ada konflik event touch dengan
    widget KivyMD/parent layout. Satu tap di area lingkaran = satu hitungan.
    """
    hitungan = NumericProperty(0)
    target_teks = StringProperty("33")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = Label(
            text="0", color=(1, 1, 1, 1), bold=True,
            halign="center", valign="middle", font_size="42sp",
            size_hint=(1, 1),
        )
        self.counter.disabled = True
        self.add_widget(self.counter)
        self.bind(pos=self._sync, size=self._sync, hitungan=self._sync, target_teks=self._sync)
        Clock.schedule_once(self._sync, 0)

    def _sync(self, *args):
        self.counter.text = str(self.hitungan)
        self.counter.pos = self.pos
        self.counter.size = self.size
        self.counter.text_size = self.size
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        r_full = min(self.width, self.height) / 2
        r_inti = r_full * 0.80
        self.counter.font_size = max(26, min(50, r_inti * 0.42))
        with self.canvas:
            app = MDApp.get_running_app()
            color = app.theme_cls.primary_color if app else (0.13, 0.59, 0.95, 1)
            gold = app.warna_emas if app else (0.79, 0.60, 0.24, 1)

            # Cincin 33 manik tasbih mengelilingi lingkaran utama, terisi
            # emas mengikuti kemajuan menuju target (atau berputar terus
            # kalau modenya "Bebas").
            jumlah_manik = 33
            try:
                target = int(self.target_teks)
            except (TypeError, ValueError):
                target = None
            if target and target > 0:
                aktif = min(jumlah_manik, int(round((self.hitungan / target) * jumlah_manik)))
            else:
                aktif = self.hitungan % jumlah_manik
            manik_r = max(2.5, r_full * 0.045)
            orbit_r = r_inti + manik_r + max(2, r_full * 0.03)
            for i in range(jumlah_manik):
                sudut = (2 * math.pi * i / jumlah_manik) - (math.pi / 2)
                mx = self.center_x + orbit_r * math.cos(sudut)
                my = self.center_y + orbit_r * math.sin(sudut)
                if i < aktif:
                    Color(rgba=gold)
                else:
                    Color(rgba=(color[0], color[1], color[2], 0.28))
                Ellipse(pos=(mx - manik_r, my - manik_r), size=(manik_r * 2, manik_r * 2))

            Color(rgba=color)
            Ellipse(
                pos=(self.center_x - r_inti, self.center_y - r_inti),
                size=(r_inti * 2, r_inti * 2),
            )

    def on_touch_down(self, touch):
        # Tangkap touch langsung pada widget, tanpa ButtonBehavior/KV callback.
        if self.collide_point(*touch.pos):
            screen = self._find_screen()
            if screen is not None:
                screen.tap()
                get_haptic()
            return True
        return super().on_touch_down(touch)

    def _find_screen(self):
        parent = self.parent
        while parent is not None:
            if isinstance(parent, TasbihScreen):
                return parent
            parent = parent.parent
        return None


class TasbihScreen(MDScreen):
    hitungan = NumericProperty(0)
    hitungan_label = StringProperty("0")
    progres_label = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hitungan = 0
        self.tercatat = 0
        self.menu_dzikir = None
        self.menu_target = None

    def on_enter(self):
        if not self.menu_dzikir:
            d_items = [{"viewclass": "OneLineListItem", "text": d, "on_release": lambda x=d: self.set_dzikir(x)} for d in ["Subhanallah", "Alhamdulillah", "Allahu Akbar", "Astaghfirullah", "La ilaha illallah"]]
            self.menu_dzikir = MDDropdownMenu(caller=self.ids.btn_dzikir, items=d_items, width_mult=4)
            t_items = [{"viewclass": "OneLineListItem", "text": t, "on_release": lambda x=t: self.set_target(x)} for t in ["33", "99", "100", "1000", "Bebas"]]
            self.menu_target = MDDropdownMenu(caller=self.ids.btn_target, items=t_items, width_mult=2)
        hari = datetime.date.today().isoformat()
        self.hitungan = db.ambil_tasbih(hari)
        self.tercatat = self.hitungan
        self.perbarui()

    def set_dzikir(self, text):
        self.ids.btn_dzikir.text = text
        self.menu_dzikir.dismiss()

    def set_target(self, text):
        self.ids.btn_target.text = text
        self.menu_target.dismiss()
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
        teks_target = self.ids.btn_target.text
        if teks_target != "Bebas":
            target = int(teks_target)
            if self.hitungan >= target and self.hitungan - 1 < target:
                kirim_notif("IbadahKu", f"MasyaAllah, {target}x {self.ids.btn_dzikir.text} selesai!")
        self.perbarui()

    def ulang(self):
        self.hitungan = 0
        self.tercatat = 0
        db.reset_tasbih(datetime.date.today().isoformat())
        self.perbarui()

    def perbarui(self, *args):
        self.hitungan_label = str(self.hitungan)
        teks_target = self.ids.btn_target.text
        if teks_target == "Bebas":
            self.progres_label = "Mode bebas (tanpa target)"
        else:
            self.progres_label = f"{self.hitungan} / {teks_target}"

def _gambar_bintang(cx, cy, r_luar, r_dalam_rasio=0.5, titik=16):
    """Kembalikan daftar titik untuk bintang delapan penjuru (motif geometris
    islami), dipakai beberapa widget dekoratif di bawah ini."""
    hasil = []
    r_dalam = r_luar * r_dalam_rasio
    for i in range(titik):
        sudut = math.pi * i / (titik / 2)
        r = r_luar if i % 2 == 0 else r_dalam
        hasil.append(cx + r * math.sin(sudut))
        hasil.append(cy + r * math.cos(sudut))
    return hasil


class GarisHias(Widget):
    """Garis dekoratif tipis dengan celah bertitik di tengah, dipakai sebagai
    pemisah antar bagian yang lebih halus daripada garis polos biasa."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._gambar, size=self._gambar)

    def _gambar(self, *args):
        self.canvas.clear()
        if self.width <= 0:
            return
        app = MDApp.get_running_app()
        emas = app.warna_emas if app else (0.79, 0.60, 0.24, 1)
        with self.canvas:
            Color(rgba=(emas[0], emas[1], emas[2], 0.55))
            mid = self.center_x
            gap = min(16, self.width * 0.08)
            Line(points=[self.x, self.center_y, mid - gap, self.center_y], width=1.2)
            Line(points=[mid + gap, self.center_y, self.right, self.center_y], width=1.2)
            r = 2.6
            Ellipse(pos=(mid - r, self.center_y - r), size=(r * 2, r * 2))


class SplashArt(Widget):
    """Latar dekoratif splash screen: lengkung mihrab & bintang delapan
    penjuru digambar lewat canvas, tanpa perlu aset gambar tambahan."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._gambar, size=self._gambar)

    def _gambar(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        app = MDApp.get_running_app()
        emas = app.warna_emas if app else (0.79, 0.60, 0.24, 1)
        with self.canvas:
            Color(rgba=(emas[0], emas[1], emas[2], 0.12))
            r = min(self.width, self.height) * 0.6
            Ellipse(pos=(self.center_x - r, self.center_y - r * 0.5), size=(r * 2, r * 1.1))

            Color(rgba=(emas[0], emas[1], emas[2], 0.18))
            lebar = min(self.width * 0.45, self.height * 0.32)
            tinggi = lebar * 1.2
            ax = self.center_x - lebar / 2
            ay = self.y + self.height * 0.06
            Ellipse(pos=(ax, ay + tinggi - lebar / 2), size=(lebar, lebar))
            Rectangle(pos=(ax, ay), size=(lebar, max(0, tinggi - lebar / 2)))

            Color(rgba=(emas[0], emas[1], emas[2], 0.45))
            titik = _gambar_bintang(self.center_x, self.y + self.height * 0.7, min(self.width, self.height) * 0.07)
            Line(points=titik, width=1.3, close=True)


class KubahHero(Widget):
    """Latar kartu 'ibadah berikutnya': lengkung kubah masjid + bintang
    delapan penjuru sebagai motif, supaya kartu ini tidak tampil polos."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._gambar, size=self._gambar)

    def _gambar(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        app = MDApp.get_running_app()
        dasar = app.theme_cls.primary_dark if app else (0.05, 0.31, 0.26, 1)
        terang = app.theme_cls.primary_color if app else (0.07, 0.44, 0.39, 1)
        emas = app.warna_emas if app else (0.79, 0.60, 0.24, 1)
        with self.canvas:
            Color(rgba=dasar)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[22, 22, 22, 22])

            Color(rgba=(terang[0], terang[1], terang[2], 0.55))
            r = self.height * 0.9
            cx = self.right - self.height * 0.30
            cy = self.top + self.height * 0.05
            Ellipse(pos=(cx - r / 2, cy - r), size=(r, r))

            Color(rgba=(emas[0], emas[1], emas[2], 0.5))
            lebar = self.height * 0.5
            tinggi = lebar * 1.25
            ax = self.right - self.height * 0.55 - lebar / 2
            ay = self.y - tinggi * 0.35
            Ellipse(pos=(ax, ay + tinggi - lebar / 2), size=(lebar, lebar))
            Rectangle(pos=(ax, ay), size=(lebar, max(0, tinggi - lebar / 2)))

            Color(rgba=(emas[0], emas[1], emas[2], 0.8))
            titik = _gambar_bintang(self.x + self.width * 0.14, self.y + self.height * 0.24, self.height * 0.09)
            Line(points=titik, width=1.3, close=True)


class WeeklyChart(Widget):
    """Grafik 7 hari yang tidak bergantung pada widget eksternal."""
    data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._gambar, size=self._gambar, data=self._gambar)

    def _gambar(self, *args):
        self.canvas.clear()
        values = []
        for item in (self.data or []):
            if isinstance(item, dict):
                values.append(float(item.get("ceklis_persen", 0) or 0))
            else:
                try:
                    values.append(float(item))
                except (TypeError, ValueError):
                    values.append(0.0)
        values = (values + [0.0] * 7)[:7]
        if not self.width or not self.height:
            return

        margin_x = min(18, self.width * 0.06)
        margin_y = min(14, self.height * 0.08)
        usable_w = max(1, self.width - margin_x * 2)
        usable_h = max(1, self.height - margin_y * 2)
        gap = usable_w * 0.035
        bar_w = max(4, (usable_w - gap * 6) / 7)

        app = MDApp.get_running_app()
        primary = app.theme_cls.primary_color if app else (0.13, 0.59, 0.95, 1)
        emas = app.warna_emas if app else (0.79, 0.60, 0.24, 1)
        puncak = max(values) if values else 0
        with self.canvas:
            Color(rgba=(0.5, 0.5, 0.5, 0.18))
            Line(points=[self.x + margin_x, self.y + margin_y,
                         self.right - margin_x, self.y + margin_y], width=1)
            for i, value in enumerate(values):
                value = max(0, min(100, value))
                h = usable_h * value / 100.0
                x = self.x + margin_x + i * (bar_w + gap)
                y = self.y + margin_y
                # Hari dengan persentase ceklis tertinggi ditonjolkan emas,
                # sisanya tetap warna primer -- kejutan kecil yang menandai
                # pencapaian terbaik minggu ini.
                if puncak > 0 and value == puncak:
                    Color(rgba=emas)
                else:
                    Color(rgba=primary)
                RoundedRectangle(pos=(x, y), size=(bar_w, max(2, h)), radius=[4, 4, 4, 4])


class BadgeCard(MDCard):
    nama = StringProperty("")
    deskripsi = StringProperty("")
    unlocked = BooleanProperty(False)


class StatistikScreen(MDScreen):
    def on_enter(self):
        self.muat_statistik()

    def muat_statistik(self):
        grid = self.ids.grid_stat
        grid.clear_widgets()
        hari = datetime.date.today().isoformat()
        awal = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()

        try:
            streak = db.hitung_streak()
            status = db.status_ceklis(hari)
            selesai = sum(1 for v in status.values() if v)
            aktif = len(db.semua_ceklis())
            # Kegiatan terjadwal juga dihitung sebagai checklist hari ini.
            status_kegiatan = db.status_kegiatan(hari)
            kegiatan = db.kegiatan_hari_ini(HARI[datetime.date.today().weekday()])
            selesai += sum(1 for k in kegiatan if status_kegiatan.get(k["id"], False))
            aktif += len(kegiatan)

            menit_hari = db.total_timer_hari_ini()
            tasbih_hari = db.ambil_tasbih(hari)
            menit_minggu, tasbih_minggu, hari_aktif = db.ringkasan_minggu(awal)
            total_menit, total_tasbih = db.total_keseluruhan()
        except Exception as exc:
            self.baris(grid, "Statistik", f"Gagal memuat data: {type(exc).__name__}")
            return

        self.baris(grid, "Streak ceklis", f"{streak} hari beruntun")
        self.baris(grid, "Ceklis hari ini", f"{selesai} dari {aktif} item selesai")
        self.baris(grid, "Timer hari ini", f"{menit_hari} menit")
        self.baris(grid, "Tasbih hari ini", f"{tasbih_hari} kali")
        self.baris(grid, "7 hari terakhir",
                   f"{menit_minggu} menit  •  {tasbih_minggu}x dzikir  •  aktif {hari_aktif} hari")
        self.baris(grid, "Total keseluruhan",
                   f"{total_menit} menit  •  {total_tasbih}x dzikir")

        # Database mengembalikan 7 dictionary; WeeklyChart juga menerima list angka.
        try:
            chart_data = db.data_grafik_mingguan(awal)
        except Exception:
            chart_data = [0] * 7
        self.ids.weekly_chart.data = chart_data

        bg = self.ids.badge_grid
        bg.clear_widgets()
        try:
            badges = achievements.semua_dengan_status()
            for b in badges:
                bg.add_widget(BadgeCard(
                    nama=b.get("judul", b.get("nama", "Badge")),
                    deskripsi=b.get("deskripsi", ""),
                    unlocked=bool(b.get("tercapai", b.get("unlocked", False))),
                ))
        except Exception:
            pass

    def baris(self, grid, judul, isi):
        from kivymd.uix.label import MDLabel
        app = MDApp.get_running_app()
        gelap = app.theme_cls.theme_style == "Dark"
        bg = app.warna_malam_kartu if gelap else app.warna_permukaan
        kartu = MDCard(
            size_hint_y=None,
            height=72,
            padding=[16, 8],
            orientation="vertical",
            radius=[14],
            elevation=0,
            md_bg_color=bg,
        )
        kartu.add_widget(MDLabel(
            text=judul,
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=22,
        ))
        kartu.add_widget(MDLabel(
            text=isi,
            font_style="Subtitle1",
            bold=True,
        ))
        grid.add_widget(kartu)


class DoaScreen(MDScreen):
    judul = StringProperty("")
    arab = StringProperty("")
    latin = StringProperty("")
    arti = StringProperty("")
    nomor = StringProperty("")
    tombol_favorit = StringProperty("bookmark-outline")

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
        self.tombol_favorit = "bookmark" if db.doa_favorit(self.indeks) else "bookmark-outline"

    def toggle_favorit(self):
        aktif = not db.doa_favorit(self.indeks)
        db.set_doa_favorit(self.indeks, aktif)
        self.tampilkan()

    def acak(self):
        if len(DOA) > 1:
            kandidat = list(range(len(DOA)))
            kandidat.remove(self.indeks)
            self.indeks = random.choice(kandidat)
            self.tampilkan()

    def sebelumnya(self):
        self.indeks = (self.indeks - 1) % len(DOA)
        self.tampilkan()

    def berikutnya(self):
        self.indeks = (self.indeks + 1) % len(DOA)
        self.tampilkan()

class KompasKiblat(Widget):
    sudut = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.uix.label import Label
        self.huruf = {}
        for h, (dx, dy) in [("U", (0, 1)), ("T", (1, 0)), ("S", (0, -1)), ("B", (-1, 0))]:
            l = Label(text=h, font_size=15, bold=True, size=(22, 22), size_hint=(None, None))
            self.add_widget(l)
            self.huruf[h] = (l, dx, dy)
        self.bind(pos=self.gambar, size=self.gambar, sudut=self.gambar)

    def gambar(self, *args):
        cx, cy = self.center
        r = min(self.width, self.height) / 2 - 24
        app = MDApp.get_running_app()
        for h, (l, dx, dy) in self.huruf.items():
            l.center = (cx + dx * (r + 12), cy + dy * (r + 12))
            l.color = app.theme_cls.text_color
        primer = app.theme_cls.primary_color
        emas = app.warna_emas if hasattr(app, "warna_emas") else (0.79, 0.60, 0.24, 1)
        self.canvas.clear()
        with self.canvas:
            Color(rgba=(primer[0], primer[1], primer[2], 0.4))
            Line(circle=(cx, cy, r), width=1.5)
            Color(rgba=primer)
            Line(circle=(cx, cy, 3))
            Line(points=[cx, cy + r - 4, cx, cy + r - 16], width=2)
            rad = math.radians(self.sudut)
            ux, uy = cx + (r - 28) * math.sin(rad), cy + (r - 28) * math.cos(rad)
            bx, by = cx - (r - 52) * math.sin(rad), cy - (r - 52) * math.cos(rad)
            Color(rgba=emas)
            Line(points=[bx, by, ux, uy], width=4)
            p1x = ux + 14 * math.sin(rad + 2.5)
            p1y = uy + 14 * math.cos(rad + 2.5)
            p2x = ux + 14 * math.sin(rad - 2.5)
            p2y = uy + 14 * math.cos(rad - 2.5)
            Triangle(points=[ux, uy, p1x, p1y, p2x, p2y])

class KiblatScreen(MDScreen):
    ARAH = ["Utara", "Timur Laut", "Timur", "Tenggara", "Selatan", "Barat Daya", "Barat", "Barat Laut"]
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
            la, lo = prayertimes.KOTA_KOORDINAT.get(nama, prayertimes.KOTA_KOORDINAT[KOTA_DEFAULT])
        b = prayertimes.arah_kiblat(la, lo)
        arah = self.ARAH[int((b + 22.5) // 45) % 8]
        self.info = f"Lokasi: {lokasi}"
        self.keterangan = (f"Arah kiblat: {arah} dari utara.\n"
                           f"Cara pakai: hadap ke arah UTARA,\n"
                           f"lalu putar {b:.0f} derajat searah jarum jam.")
        self.ids.kompas.sudut = b

class PengaturanScreen(MDScreen):
    def on_enter(self):
        self._sedang_muat = True
        if not hasattr(self, 'menu_kota'):
            k_items = [{"viewclass": "OneLineListItem", "text": k, "on_release": lambda x=k: self.set_kota(x)} for k in DAFTAR_KOTA]
            self.menu_kota = MDDropdownMenu(caller=self.ids.btn_kota, items=k_items, width_mult=3)
            a_items = [{"viewclass": "OneLineListItem", "text": a, "on_release": lambda x=a: self.set_alarm_menit(x)} for a in ["5", "10", "15", "30"]]
            self.menu_alarm = MDDropdownMenu(caller=self.ids.btn_alarm_menit, items=a_items, width_mult=2)
            
        self.ids.btn_kota.text = db.ambil_pengaturan("kota", KOTA_DEFAULT)
        self.ids.sw_alarm.active = db.ambil_pengaturan("alarm_aktif", "0") == "1"
        self.ids.btn_alarm_menit.text = db.ambil_pengaturan("alarm_menit", "10")
        app = MDApp.get_running_app()
        self.ids.sw_gelap.active = app.theme_cls.theme_style == "Dark"
        
        if db.ambil_pengaturan("lat"):
            self.ids.lbl_lokasi.text = ("Mode otomatis aktif: " + db.ambil_pengaturan("kota", KOTA_DEFAULT))
        else:
            self.ids.lbl_lokasi.text = "Mode manual (kota dipilih sendiri)"
        self.ids.lbl_status.text = ""
        self._sedang_muat = False

    def set_kota(self, text):
        self.ids.btn_kota.text = text
        self.menu_kota.dismiss()
        self.simpan_kota()
        
    def set_alarm_menit(self, text):
        self.ids.btn_alarm_menit.text = text
        self.menu_alarm.dismiss()
        self.pilih_menit()

    def ubah_alarm(self, saklar, aktif):
        if getattr(self, "_sedang_muat", False): return
        db.simpan_pengaturan("alarm_aktif", "1" if aktif else "0")

    def pilih_menit(self):
        if getattr(self, "_sedang_muat", False): return
        db.simpan_pengaturan("alarm_menit", self.ids.btn_alarm_menit.text)

    def simpan_kota(self):
        kota = self.ids.btn_kota.text
        db.simpan_pengaturan("kota", kota)
        db.simpan_pengaturan("lat", "")
        db.simpan_pengaturan("lon", "")
        self.ids.lbl_lokasi.text = "Mode manual (kota dipilih sendiri)"
        self.ids.lbl_status.text = f"Kota manual tersimpan: {kota}"

    def deteksi_lokasi(self):
        self.ids.lbl_lokasi.text = "Mendeteksi lokasi (butuh internet)..."
        threading.Thread(target=self._deteksi, daemon=True).start()

    def _deteksi(self):
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
                f"Buka ulang Beranda untuk memuat jadwalnya")
        Clock.schedule_once(lambda dt: self._set_lokasi(info))

    def _set_lokasi(self, teks):
        self.ids.lbl_lokasi.text = teks
        if self.manager and self.manager.has_screen("home"):
            self.manager.get_screen("home").on_enter()

    def ubah_mode(self, saklar, aktif):
        if getattr(self, "_sedang_muat", False): return
        app = MDApp.get_running_app()
        app.theme_cls.theme_style = "Dark" if aktif else "Light"
        db.simpan_pengaturan("mode_gelap", "1" if aktif else "0")
        
    def ubah_warna(self, palette):
        app = MDApp.get_running_app()
        app.theme_cls.primary_palette = palette
        db.simpan_pengaturan("tema_warna", palette)

class IbadahKuApp(MDApp):
    font_arab = StringProperty("")

    # Token warna kustom (tidak berubah walau tema terang/gelap di-toggle,
    # dipakai widget kustom & sebagai aksen di atas primary_palette KivyMD)
    warna_teal = ListProperty(PALET["teal"])
    warna_teal_soft = ListProperty(PALET["teal_soft"])
    warna_emas = ListProperty(PALET["emas"])
    warna_emas_soft = ListProperty(PALET["emas_soft"])
    warna_kertas = ListProperty(PALET["kertas"])
    warna_kertas_dim = ListProperty(PALET["kertas_dim"])
    warna_permukaan = ListProperty(PALET["permukaan"])
    warna_malam = ListProperty(PALET["malam"])
    warna_malam_kartu = ListProperty(PALET["malam_kartu"])
    warna_ivory = ListProperty(PALET["ivory"])
    warna_tinta = ListProperty(PALET["tinta"])

    def build(self):
        self.theme_cls.material_style = "M3"
        self.theme_cls.primary_palette = db.ambil_pengaturan("tema_warna", "Teal")
        self.theme_cls.theme_style = "Dark" if db.ambil_pengaturan("mode_gelap", "0") == "1" else "Light"
        db.buat_tabel()
        self.font_arab = cari_font_arab()

        self.jadwal = _baca_jadwal_cache()
        self.alarm_terkirim = set()
        try:
            self.bunyi = SoundLoader.load(buat_file_bunyi())
        except Exception:
            self.bunyi = None
        Clock.schedule_interval(self.cek_alarm, 20)

        sm = ScreenManager()
        sm.add_widget(SplashScreen(name="splash"))
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
        
    def on_start(self):
        self.root.current = "splash"

    def cek_alarm(self, *args):
        if db.ambil_pengaturan("alarm_aktif", "0") != "1":
            return
        sekarang = datetime.datetime.now()
        tanggal_hari_ini = sekarang.date().isoformat()
        if getattr(self, "tanggal_alarm", None) != tanggal_hari_ini:
            self.tanggal_alarm = tanggal_hari_ini
            self.alarm_terkirim.clear()
            self.jadwal = _baca_jadwal_cache() or []
        agenda = list(self.jadwal or [])
        for k in db.kegiatan_hari_ini(HARI[sekarang.weekday()]):
            agenda.append((k["id"], k["nama"], k["jam"]))
        if not agenda:
            return
        try:
            offset = int(db.ambil_pengaturan("alarm_menit", "10"))
        except:
            offset = 10
        for item in agenda:
            if len(item) == 2:
                sumber_id, nama, jam = "shalat", item[0], item[1]
            else:
                sumber_id, nama, jam = item
            try:
                h, m = map(int, jam.split(":"))
            except:
                continue
            waktunya = sekarang.replace(hour=h, minute=m, second=0, microsecond=0)
            pengingat = waktunya - datetime.timedelta(minutes=offset)
            kunci = f"{tanggal_hari_ini}|{sumber_id}|{nama}@{jam}"
            if pengingat <= sekarang < waktunya and kunci not in self.alarm_terkirim:
                self.alarm_terkirim.add(kunci)
                pesan = f"{nama} pukul {jam} - sekitar {offset} menit lagi"
                kirim_notif("Pengingat IbadahKu", pesan)
                if self.bunyi:
                    try:
                        self.bunyi.play()
                    except: pass
                PopupAlarm("Segera Waktunya!", pesan).open()

if __name__ == "__main__":
    IbadahKuApp().run()
