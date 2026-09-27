"""Jembatan ke API Aladhan + deteksi lokasi + hitung arah kiblat."""

import datetime
import json
import math
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_KOTA = "https://api.aladhan.com/v1/timingsByCity"
API_KOORDINAT = "https://api.aladhan.com/v1/timings"
API_IP = "https://ipapi.co/json/"
METODE_KEMENAG = 20

NAMA_WAKTU = ["Subuh", "Dzuhur", "Ashar", "Maghrib", "Isya"]
KUNCI_API = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

# koordinat kasar kota (untuk arah kiblat saat mode manual)
KOTA_KOORDINAT = {
    "Jakarta": (-6.20, 106.82), "Bandung": (-6.92, 107.61),
    "Bekasi": (-6.24, 107.00), "Bogor": (-6.60, 106.80),
    "Tangerang": (-6.18, 106.63), "Depok": (-6.40, 106.82),
    "Semarang": (-6.97, 110.42), "Yogyakarta": (-7.80, 110.37),
    "Surabaya": (-7.25, 112.75), "Malang": (-7.98, 112.63),
    "Medan": (3.59, 98.67), "Palembang": (-2.98, 104.75),
    "Makassar": (-5.13, 119.40), "Denpasar": (-8.65, 115.22),
}

KAABAH = (21.4225, 39.8262)


class _Response:
    def __init__(self, response):
        self._response = response

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self._response.read().decode("utf-8"))


def _get(url, params=None, timeout=10):
    if params:
        url = f"{url}?{urlencode(params)}"
    return _Response(urlopen(Request(url, headers={"User-Agent": "IbadahKu/1.0"}),
                             timeout=timeout))


def _olah(data):
    timings = data["timings"]
    jadwal = []
    for nama, kunci in zip(NAMA_WAKTU, KUNCI_API):
        j, m = timings[kunci][:5].split(":")
        jadwal.append((nama, f"{int(j):02d}:{int(m):02d}"))
    return jadwal


def ambil_jadwal(kota):
    r = _get(API_KOTA, params={"city": kota, "country": "Indonesia",
                                "method": METODE_KEMENAG}, timeout=10)
    r.raise_for_status()
    return _olah(r.json()["data"])


def ambil_jadwal_koordinat(lat, lon):
    """Jadwal sholat dari koordinat GPS/IP (lebih presisi dari nama kota)."""
    tgl = datetime.date.today().strftime("%d-%m-%Y")
    r = _get(f"{API_KOORDINAT}/{tgl}",
             params={"latitude": lat, "longitude": lon,
                     "method": METODE_KEMENAG}, timeout=10)
    r.raise_for_status()
    return _olah(r.json()["data"])


def deteksi_lokasi():
    """Deteksi lokasi lewat IP (akurat level kota, tanpa API key).
    Return (nama_kota, lat, lon). GPS perangkat diaktifkan saat build APK."""
    r = _get(API_IP, timeout=10)
    r.raise_for_status()
    data = r.json()
    return (data.get("city", "Lokasi Saya"),
            float(data["latitude"]), float(data["longitude"]))


def arah_kiblat(lat, lon):
    """Arah Ka'bah dalam derajat (0 = utara, 90 = timur, dst)."""
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2, lo2 = math.radians(KAABAH[0]), math.radians(KAABAH[1])
    dlon = lo2 - lo1
    x = math.sin(dlon) * math.cos(la2)
    y = (math.cos(la1) * math.sin(la2)
         - math.sin(la1) * math.cos(la2) * math.cos(dlon))
    return math.degrees(math.atan2(x, y)) % 360