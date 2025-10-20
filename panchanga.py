from datetime import date
import math

# Basic Panchanga calculations (approximate but consistent)

def gregorian_to_julian(y, m, d):
    """Convert a Gregorian date to Julian day number."""
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + (A // 4)
    JD = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    return JD

def lunar_longitude(jd):
    """Approximate mean longitude of Moon in degrees."""
    D = jd - 2451550.1
    N = 125.1228 - 0.0529538083 * D
    i = 5.1454
    w = 318.0634 + 0.1643573223 * D
    a = 60.2666  # Earth radii
    e = 0.0549
    M = 115.3654 + 13.0649929509 * D

    M = math.radians(M % 360)
    Ec = 2 * e * math.sin(M)
    lon = (math.degrees(M) + Ec + w) % 360
    return lon

def solar_longitude(jd):
    """Approximate mean longitude of Sun in degrees."""
    D = jd - 2451545.0
    g = 357.529 + 0.98560028 * D
    q = 280.459 + 0.98564736 * D
    L = (q + 1.915 * math.sin(math.radians(g)) + 0.020 * math.sin(math.radians(2 * g))) % 360
    return L

def get_tithi(jd):
    """Return current Tithi number and name."""
    moon_long = lunar_longitude(jd)
    sun_long = solar_longitude(jd)
    diff = (moon_long - sun_long) % 360
    tithi_num = int(diff // 12) + 1  # 30 tithis in a lunar month

    tithi_names = [
        "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
        "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
        "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
    ]
    fortnight = "Shukla Paksha" if diff < 180 else "Krishna Paksha"
    tithi_name = tithi_names[(tithi_num - 1) % 15]

    return f"{tithi_name} ({fortnight})"

def tithi(dob):
    """Main function: takes datetime.date and returns Tithi."""
    jd = gregorian_to_julian(dob.year, dob.month, dob.day)
    return get_tithi(jd)