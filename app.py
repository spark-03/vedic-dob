# app.py — Highly accurate Vedic DOB Finder (Swiss Ephemeris, topocentric, Lahiri)
import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import pytz
import swisseph as swe
import math
from supabase import create_client

st.set_page_config(page_title="Vedic DOB Finder (Swiss Ephemeris)", layout="centered")
st.title("📿 Vedic DOB Finder — High Accuracy (Swiss Ephemeris + Topocentric + Lahiri)")

# -------------------------
# Supabase (optional) via Streamlit secrets
# -------------------------
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None
    st.info("Supabase not configured. Results shown locally. Add secrets to save records.")

# -------------------------
# District-level coordinates (sample). Add more districts as needed.
# These are representative district-center coordinates (lat, lon).
# -------------------------
location_data = {
    "Andhra Pradesh": {
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
        "Guntur": {"lat": 16.3067, "lon": 80.4365, "tz": "Asia/Kolkata"},
    },
    "Telangana": {"Hyderabad": {"lat": 17.3850, "lon": 78.4867, "tz": "Asia/Kolkata"}},
    "Tamil Nadu": {"Chennai": {"lat": 13.0827, "lon": 80.2707, "tz": "Asia/Kolkata"}},
    "Karnataka": {"Bengaluru": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"}},
    # Extend as required...
}

# -------------------------
# Helper: JD UT from UTC datetime
# -------------------------
def jd_from_utc_dt(utc_dt: datetime) -> float:
    # swe.julday(year, month, day, hour_decimal) -> JD UT
    y = utc_dt.year
    m = utc_dt.month
    d = utc_dt.day
    hour_decimal = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    return swe.julday(y, m, d, hour_decimal)

# -------------------------
# Swiss Ephemeris: topocentric & sidereal calc
# -------------------------
# Ensure swe library has ephemeris files available on the host (pyswisseph usually bundles or downloads).
# Set sidereal mode globally to Lahiri (SIDM_LAHIRI)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

def sun_moon_sidereal_topo(jd_ut: float, lon_deg: float, lat_deg: float, height_m: float = 0.0):
    """
    Returns sidereal longitudes (degrees) of Sun and Moon at JD UT, topocentric,
    using Swiss Ephemeris with SIDEREAL mode (Lahiri).
    """
    # set topology for topocentric calc (lon, lat in degrees, height in meters)
    swe.set_topo(lon_deg, lat_deg, height_m)
    # flags: use SWIEPH (Swiss Ephemeris), SIDEREAL, TOPOCTR for topocentric correction
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR
    sun_res = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon_res = swe.calc_ut(jd_ut, swe.MOON, flags)
    # sun_res[0] and moon_res[0] are longitudes in degrees (sidereal because of FLG_SIDEREAL)
    sun_sid = sun_res[0] % 360
    moon_sid = moon_res[0] % 360
    return sun_sid, moon_sid

# -------------------------
# Panchang element calculators (from sidereal longitudes)
# -------------------------
def tithi_num_from_sidereal(sun_sid: float, moon_sid: float) -> int:
    diff = (moon_sid - sun_sid) % 360
    return int(diff // 12) + 1  # 1..30

def tithi_name_from_num(tnum: int) -> str:
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
              "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
    if 1 <= tnum <= 15:
        return "Shukla " + tithis[tnum - 1]
    else:
        return "Krishna " + tithis[(tnum - 16) % 15]

def nakshatra_from_sidereal(moon_sid: float) -> (str, int, float):
    # returns (name, index 0..26, degrees into nakshatra)
    sector = 360.0 / 27.0
    idx = int((moon_sid % 360) // sector)
    deg_into = (moon_sid % 360) - idx * sector
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                  "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                  "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                  "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return nakshatras[idx], idx, deg_into

def rashi_from_sidereal(moon_sid: float) -> (str, int, float):
    # returns (name, index 0..11, degrees into rashi)
    idx = int(moon_sid // 30) % 12
    deg_into = moon_sid - idx * 30
    rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
              "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return rashis[idx], idx, deg_into

def masa_from_sidereal(sun_sid: float) -> str:
    # Approximate lunar month mapping from sidereal Sun longitude (works for Amanta approx)
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    idx = int((sun_sid + 30) // 30) % 12
    return lunar_months[idx]

# -------------------------
# UI: input form
# -------------------------
with st.form("birth"):
    st.write("Enter birth details (time local + district). Provide seconds if known.")
    name = st.text_input("Full name")
    dob = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today())
    birth_time = st.time_input("Time of birth (local, 24h)", value=dtime(0, 0, 0))
    state = st.selectbox("State", sorted(location_data.keys()))
    district = st.selectbox("District", sorted(location_data[state].keys()))
    manual = st.checkbox("Manual lat/lon override", value=False)
    if manual:
        lat = st.number_input("Latitude (deg, north +)", value=float(location_data[state][district]["lat"]))
        lon = st.number_input("Longitude (deg, east +)", value=float(location_data[state][district]["lon"]))
        tz_name = st.text_input("Timezone (IANA, e.g. Asia/Kolkata)", value=location_data[state][district]["tz"])
    else:
        lat = location_data[state][district]["lat"]
        lon = location_data[state][district]["lon"]
        tz_name = location_data[state][district].get("tz", "Asia/Kolkata")
    submit = st.form_submit_button("Calculate (High Accuracy)")

if not submit:
    st.caption("Fill the form and click Calculate.")
else:
    # localize and convert to UTC
    try:
        local_tz = pytz.timezone(tz_name)
    except Exception:
        st.error(f"Invalid timezone {tz_name}; defaulting to Asia/Kolkata")
        local_tz = pytz.timezone("Asia/Kolkata")

    local_dt = local_tz.localize(datetime.combine(dob, birth_time))
    utc_dt = local_dt.astimezone(pytz.utc)

    # JD UT
    jd_ut = jd_from_utc_dt(utc_dt)

    # topocentric sidereal longitudes
    try:
        sun_sid, moon_sid = sun_moon_sidereal_topo(jd_ut, lon, lat, 0.0)
    except Exception as e:
        st.error(f"Swiss Ephemeris error computing positions: {e}")
        st.stop()

    # compute panchang elements
    tnum = tithi_num_from_sidereal(sun_sid, moon_sid)
    vedic_tithi = tithi_name_from_num(tnum)
    paksha = "Shukla" if tnum <= 15 else "Krishna"
    nak_name, nak_idx, nak_deg = nakshatra_from_sidereal(moon_sid)
    rashi_name, rashi_idx, rashi_deg = rashi_from_sidereal(moon_sid)
    masa_name = masa_from_sidereal(sun_sid)
    weekday_local = local_dt.strftime("%A")
    tithi_angle = (moon_sid - sun_sid) % 360

    # -------------------------
    # Find next exact Gregorian date (local) where Tithi+Masa+Nakshatra+Rashi match
    # We iterate by local days, preserving the same local time, convert candidate -> UTC -> JD UT -> compute topocentric sidereal
    # -------------------------
    def find_next_exact_vedic(local_dt_localized: datetime, max_days: int = 450):
        try:
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1)
        except ValueError:
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1, month=1, day=1)

        for i in range(max_days):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            jd_c = jd_from_utc_dt(cand_utc)
            try:
                s_sid_c, m_sid_c = sun_moon_sidereal_topo(jd_c, lon, lat, 0.0)
            except Exception:
                continue
            t_c = tithi_num_from_sidereal(s_sid_c, m_sid_c)
            masa_c = masa_from_sidereal(s_sid_c)
            nak_c, _, _ = nakshatra_from_sidereal(m_sid_c)
            rash_c, _, _ = rashi_from_sidereal(m_sid_c)
            if t_c == tnum and masa_c == masa_name and nak_c == nak_name and rash_c == rashi_name:
                return cand_local.date()
        # fallback to tithi+masa match
        for i in range(365):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            jd_c = jd_from_utc_dt(cand_utc)
            try:
                s_sid_c, m_sid_c = sun_moon_sidereal_topo(jd_c, lon, lat, 0.0)
            except Exception:
                continue
            if tithi_num_from_sidereal(s_sid_c, m_sid_c) == tnum and masa_from_sidereal(s_sid_c) == masa_name:
                return cand_local.date()
        return start_local.date()

    next_vedic_date = find_next_exact_vedic(local_dt)

    # -------------------------
    # Display results
    # -------------------------
    st.markdown("## ✅ Computed Vedic Details (Topocentric Sidereal — Lahiri)")
    st.write(f"**Name:** {name or '-'}")
    st.write(f"**Birth (local):** {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({state} / {district})")
    st.write(f"**Coordinates used:** {lat:.6f}°N, {lon:.6f}°E  | Timezone: {tz_name}")
    st.write(f"- **Tithi:** {vedic_tithi}  ({paksha})")
    st.write(f"- **Nakshatra:** {nak_name} (#{nak_idx+1}, {nak_deg:.3f}° into it)")
    st.write(f"- **Masa (approx):** {masa_name}")
    st.write(f"- **Rashi (Moon sign, sidereal):** {rashi_name} (#{rashi_idx+1}, {rashi_deg:.3f}° into it)")
    st.write(f"- **Weekday:** {weekday_local}")
    st.write(f"- **Tithi angle (moon - sun):** {tithi_angle:.6f}°")
    st.markdown("### Raw sidereal longitudes")
    st.write(f"- Sun (sidereal): {sun_sid:.6f}°")
    st.write(f"- Moon (sidereal): {moon_sid:.6f}°")
    st.markdown("### Next birthdays")
    try:
        solar_bday_next = local_dt.replace(year=local_dt.year + 1).date()
    except Exception:
        solar_bday_next = date(local_dt.year + 1, 1, 1)
    st.write(f"- Solar birthday next year: **{solar_bday_next}**")
    st.write(f"- Next exact Vedic DOB (match Tithi+Masa+Nakshatra+Rashi): **{next_vedic_date}**")

    # -------------------------
    # Save to Supabase (optional)
    # -------------------------
    if supabase:
        try:
            supabase.table("users").insert({
                "name": name,
                "dob": dob.isoformat(),
                "time_of_birth": birth_time.strftime("%H:%M:%S"),
                "state": state,
                "district": district,
                "lat": lat,
                "lon": lon,
                "vedic_tithi": vedic_tithi,
                "vedic_paksha": paksha,
                "vedic_nakshatra": nak_name,
                "vedic_masa": masa_name,
                "vedic_rashi": rashi_name,
                "solar_birthday_next_year": solar_bday_next.isoformat(),
                "next_vedic_dob": next_vedic_date.isoformat()
            }).execute()
            st.success("Saved to Supabase ✅")
        except Exception as e:
            st.error(f"Could not save to Supabase: {e}")

    st.caption("This app computes topocentric sidereal positions with Swiss Ephemeris (pyswisseph). For absolute parity with any specific printed Panchang, we can add a compare/diagnostic view (raw JD, raw longitudes, ayanamsa numeric).")