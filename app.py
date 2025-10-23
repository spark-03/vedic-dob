import swisseph as swe
import pytz
from datetime import datetime, timedelta

# Lahiri Ayanamsa for sidereal positions
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Coordinates database (add more districts as needed)
district_coords = {
    "Andhra Pradesh": {
        "Nellore": (14.4426, 79.9865),
        "Visakhapatnam": (17.6868, 83.2185),
        "Vijayawada": (16.5062, 80.6480),
        "Tirupati": (13.6288, 79.4192),
    },
}

# ------------------------------------------------------------
# Helper: Sun and Moon positions (sidereal)
# ------------------------------------------------------------
def sun_moon_sidereal_topo(jd_ut, lon, lat):
    """Compute sidereal longitudes of Sun and Moon (topocentric, Lahiri ayanamsa)."""
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR
    swe.set_topo(lon, lat, 0)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    sun_res, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon_res, _ = swe.calc_ut(jd_ut, swe.MOON, flags)

    sun_lon = sun_res[0] % 360
    moon_lon = moon_res[0] % 360
    return sun_lon, moon_lon


# ------------------------------------------------------------
# Compute Tithi, Nakshatra, Masa, Rashi
# ------------------------------------------------------------
def tithi_nakshatra_masa_rashi(jd_ut, lon, lat):
    sun_lon, moon_lon = sun_moon_sidereal_topo(jd_ut, lon, lat)
    diff = (moon_lon - sun_lon + 360) % 360

    # --- Tithi ---
    tithi_num = int(diff // 12) + 1
    paksha = "Shukla" if diff < 180 else "Krishna"
    tithi_names = [
        "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
        "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi",
        "Chaturdashi", "Purnima / Amavasya"
    ]
    tithi = f"{paksha} {tithi_names[(tithi_num - 1) % 15]}"

    # --- Nakshatra ---
    nakshatra_num = int((moon_lon % 360) // (360 / 27))
    nakshatra_names = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
        "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
        "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
        "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]
    nakshatra = nakshatra_names[nakshatra_num]

    # --- Rashi (Moon Sign) ---
    rashi_num = int((moon_lon % 360) // 30)
    rashi_names = [
        "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
        "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"
    ]
    rashi = rashi_names[rashi_num]

    # --- Masa ---
    sun_masa = int((sun_lon % 360) // 30)
    masa_names = [
        "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
        "Bhadrapada", "Ashwin", "Kartika", "Margashira", "Pushya",
        "Magha", "Phalguna"
    ]
    masa = masa_names[sun_masa]

    return tithi, nakshatra, masa, rashi


# ------------------------------------------------------------
# Find next same Vedic DOB
# ------------------------------------------------------------
def find_next_exact_vedic(jd_ut, lon, lat):
    ref_tithi, ref_nakshatra, ref_masa, ref_rashi = tithi_nakshatra_masa_rashi(jd_ut, lon, lat)
    for i in range(1, 500):  # search next 500 days
        jd_next = jd_ut + i
        tithi, nakshatra, masa, rashi = tithi_nakshatra_masa_rashi(jd_next, lon, lat)
        if (tithi == ref_tithi and nakshatra == ref_nakshatra
                and masa == ref_masa and rashi == ref_rashi):
            return swe.revjul(jd_next)
    return None


# ------------------------------------------------------------
# Main Program
# ------------------------------------------------------------
if __name__ == "__main__":
    print("📿 Vedic DOB Calculator\n")

    name = input("Enter full name: ")
    dob_str = input("Enter date of birth (YYYY-MM-DD): ")
    tob_str = input("Enter time of birth (HH:MM in 24h): ")

    state = input("Enter State (e.g., Andhra Pradesh): ")
    district = input("Enter District (e.g., Nellore): ")

    lat, lon = district_coords[state][district]
    tz = pytz.timezone("Asia/Kolkata")

    dob_dt = datetime.strptime(f"{dob_str} {tob_str}", "%Y-%m-%d %H:%M")
    dob_dt_local = tz.localize(dob_dt)
    jd_ut = swe.julday(dob_dt_local.year, dob_dt_local.month, dob_dt_local.day,
                       dob_dt_local.hour + dob_dt_local.minute / 60.0)

    tithi, nakshatra, masa, rashi = tithi_nakshatra_masa_rashi(jd_ut, lon, lat)

    weekday = dob_dt_local.strftime("%A")
    next_vedic = find_next_exact_vedic(jd_ut, lon, lat)
    next_gregorian = swe.revjul(jd_ut + 365)

    print("\n✅ Computed Vedic Details (Sidereal — Lahiri):")
    print(f"Name: {name}")
    print(f"Birth (local): {dob_dt_local.strftime('%Y-%m-%d %H:%M')} ({state} / {district})")
    print(f"Coordinates used: {lat:.4f}°N, {lon:.4f}°E — timezone Asia/Kolkata\n")
    print(f"Tithi: {tithi}")
    print(f"Nakshatra: {nakshatra}")
    print(f"Masa: {masa}")
    print(f"Rashi (Moon sign): {rashi}")
    print(f"Weekday: {weekday}\n")

    print("Next birthdays:")
    print(f"- Solar birthday next year: {next_gregorian[0]}-{next_gregorian[1]:02d}-{next_gregorian[2]:02d}")
    if next_vedic:
        y, m, d, _ = next_vedic
        print(f"- Next exact Vedic DOB (same Tithi+Nakshatra+Masa+Rashi): {y}-{m:02d}-{d:02d}")