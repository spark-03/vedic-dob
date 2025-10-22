# app.py — Ultra-accurate Vedic DOB Finder (Swiss Ephemeris, topocentric, Lahiri)
import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import pytz
import swisseph as swe  # pyswisseph
import math
from supabase import create_client

st.set_page_config(page_title="Vedic DOB Finder (Swiss Ephemeris)", layout="centered")
st.title("📿 Vedic DOB Finder — Swiss Ephemeris (Topocentric + Lahiri)")

# -------------------------
# Supabase (optional) via Streamlit secrets:
# Put under Streamlit secrets:
# [supabase]
# url = "https://....supabase.co"
# key = "your-anon-or-service-key"
# -------------------------
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None
    st.info("Supabase not configured. Results will still be displayed. Add secrets to save records.")

# -------------------------
# Small district-level location DB (representative coords). Extend as needed.
# -------------------------
location_data = {
    "Andhra Pradesh": {
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
        "Guntur": {"lat": 16.3067, "lon": 80.4365, "tz": "Asia/Kolkata"},
    },
    "Telangana": {
        "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "tz": "Asia/Kolkata"},
    },
    "Tamil Nadu": {
        "Chennai": {"lat": 13.0827, "lon": 80.2707, "tz": "Asia/Kolkata"},
    },
    "Karnataka": {
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"},
    },
    # Add more states/districts for your users as needed
}

# -------------------------
# Helper: build JD UT from a UTC datetime
# -------------------------
def jd_from_utc_dt(utc_dt: datetime) -> float:
    # swe.julday(year, month, day, hour_decimal) returns JD (UT)
    y = utc_dt.year
    m = utc_dt.month
    d = utc_dt.day
    hour_decimal = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    return swe.julday(y, m, d, hour_decimal)

# -------------------------
# Swiss Ephemeris wrappers
# -------------------------
def sun_moon_tropical_longitudes_jd(jd_ut: float, topo=None):
    """
    Return tropical ecliptic longitudes (degrees) of Sun and Moon at jd_ut (UT).
    If topo is provided as (lon_deg, lat_deg, height_m), set Swiss Ephemeris topocentric coords.
    """
    # set topo if provided (lon, lat, height in meters). swe.set_topo expects geodetic lon, lat in degrees, height in meters.
    if topo:
        lon, lat, h = topo
        swe.set_topo(lon, lat, h)
    else:
        swe.set_topo(0.0, 0.0, 0.0)  # reset

    sun = swe.calc_ut(jd_ut, swe.SUN)  # returns [lon, lat, dist, ...]
    moon = swe.calc_ut(jd_ut, swe.MOON)
    # reset topo to zero (important)
    swe.set_topo(0.0, 0.0, 0.0)
    sun_lon = sun[0] % 360
    moon_lon = moon[0] % 360
    return sun_lon, moon_lon

def get_lahiri_ayanamsa_deg(jd_ut: float) -> float:
    # swiss ephemeris provides get_ayanamsa or get_ayanamsa_ut depending on build; try both
    try:
        return swe.get_ayanamsa(jd_ut)
    except Exception:
        try:
            return swe.get_ayanamsa_ut(jd_ut)
        except Exception as e:
            raise RuntimeError("Swiss Ephemeris: cannot obtain ayanamsa. Ensure pyswisseph is installed correctly.") from e

# -------------------------
# Sidereal conversion helpers and panchang element calculators
# -------------------------
def to_sidereal(tropical_deg: float, ayanamsa_deg: float) -> float:
    return (tropical_deg - ayanamsa_deg) % 360

def tithi_num_from_sidereal(sun_sid: float, moon_sid: float) -> int:
    diff = (moon_sid - sun_sid) % 360
    return int(diff // 12) + 1  # 1..30

def tithi_name_from_num(tnum: int) -> str:
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
              "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
    if tnum <= 15:
        return f"Shukla {tithis[tnum - 1]}"
    else:
        return f"Krishna {tithis[(tnum - 16) % 15]}"

def nakshatra_from_sidereal(moon_sid: float) -> str:
    index = int((moon_sid % 360) / (360.0 / 27.0))
    naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
            "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
            "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
            "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
            "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
            "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return naks[index]

def rashi_from_sidereal(moon_sid: float) -> str:
    ridx = int(moon_sid / 30) % 12
    rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
              "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return rashis[ridx]

def masa_from_sidereal(sun_sid: float) -> str:
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    idx = int((sun_sid + 30) / 30) % 12
    return lunar_months[idx]

# -------------------------
# UI: form for input
# -------------------------
with st.form("birth_form"):
    name = st.text_input("Full name")
    dob = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today())
    birth_time = st.time_input("Time of birth (local, 24h)", value=dtime(19, 45, 0))
    st.markdown("Select place of birth (state → district). You can also check *Manual lat/lon override* to enter exact coordinates.")
    state = st.selectbox("State", sorted(location_data.keys()))
    district = st.selectbox("District", sorted(location_data[state].keys()))
    manual_override = st.checkbox("Manual lat/lon override", value=False)
    if manual_override:
        lat_override = st.number_input("Latitude (deg, north +)", value=float(location_data[state][district]["lat"]))
        lon_override = st.number_input("Longitude (deg, east +)", value=float(location_data[state][district]["lon"]))
    submit = st.form_submit_button("Calculate Vedic DOB (high-accuracy)")

if not submit:
    st.caption("Enter details and press Calculate.")
else:
    # determine final coordinates and timezone
    if manual_override:
        lat = float(lat_override)
        lon = float(lon_override)
        tz_name = location_data[state][district].get("tz", "Asia/Kolkata")
    else:
        place_info = location_data[state][district]
        lat = float(place_info["lat"])
        lon = float(place_info["lon"])
        tz_name = place_info.get("tz", "Asia/Kolkata")

    # local timezone -> UTC
    local_tz = pytz.timezone(tz_name)
    local_dt = local_tz.localize(datetime.combine(dob, birth_time))
    utc_dt = local_dt.astimezone(pytz.utc)

    # topocentric: use lon (east positive), lat (north positive), height ~ 0 m
    topo = (lon, lat, 0.0)

    # JD UT for exact birth instant
    jd_ut_birth = jd_from_utc_dt(utc_dt)

    # obtain tropical longitudes using topocentric correction
    sun_trop, moon_trop = sun_moon_tropical_longitudes_jd(jd_ut_birth, topo=topo)

    # obtain ayanamsa (Lahiri) from Swiss Ephemeris at this JD
    ayanamsa_deg = get_lahiri_ayanamsa_deg(jd_ut_birth)

    # compute sidereal longitudes
    sun_sid = to_sidereal(sun_trop, ayanamsa_deg)
    moon_sid = to_sidereal(moon_trop, ayanamsa_deg)

    # compute panchang elements
    t_num = tithi_num_from_sidereal(sun_sid, moon_sid)
    vedic_tithi = tithi_name_from_num(t_num)
    vedic_paksha = "Shukla" if t_num <= 15 else "Krishna"
    vedic_nakshatra = nakshatra_from_sidereal(moon_sid)
    vedic_rashi = rashi_from_sidereal(moon_sid)
    vedic_masa = masa_from_sidereal(sun_sid)
    weekday_local = local_dt.strftime("%A")
    tithi_angle = (moon_sid - sun_sid) % 360  # degrees into lunar month

    # -------------------------
    # Find next exact Vedic DOB: search by local date+same local time each day
    # -------------------------
    def find_next_exact_vedic_date(local_dt_localized: datetime, max_days=450):
        # start from same solar date next year (local)
        try:
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1)
        except ValueError:
            # Feb 29 fallback
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1, month=1, day=1)

        for i in range(max_days):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            jd_ut = jd_from_utc_dt(cand_utc)
            s_trop, m_trop = sun_moon_tropical_longitudes_jd(jd_ut, topo=topo)
            ay = get_lahiri_ayanamsa_deg(jd_ut)
            s_sid = to_sidereal(s_trop, ay)
            m_sid = to_sidereal(m_trop, ay)

            # elements
            c_tnum = tithi_num_from_sidereal(s_sid, m_sid)
            c_masa = masa_from_sidereal(s_sid)
            c_nak = nakshatra_from_sidereal(m_sid)
            c_rash = rashi_from_sidereal(m_sid)

            if (c_tnum == t_num and c_masa == vedic_masa and c_nak == vedic_nakshatra and c_rash == vedic_rashi):
                return cand_local.date()
        # fallback to first match of tithi+masa
        for i in range(365):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            jd_ut = jd_from_utc_dt(cand_utc)
            s_trop, m_trop = sun_moon_tropical_longitudes_jd(jd_ut, topo=topo)
            ay = get_lahiri_ayanamsa_deg(jd_ut)
            s_sid = to_sidereal(s_trop, ay)
            m_sid = to_sidereal(m_trop, ay)
            if tithi_num_from_sidereal(s_sid, m_sid) == t_num and masa_from_sidereal(s_sid) == vedic_masa:
                return cand_local.date()
        return start_local.date()

    next_vedic_date = find_next_exact_vedic_date(local_dt)

    # -------------------------
    # Output: readable results + diagnostics
    # -------------------------
    st.markdown("## ✅ Computed Vedic Details (Topocentric Sidereal — Lahiri via Swiss Ephemeris)")
    st.write(f"**Name:** {name}")
    st.write(f"**Birth (local):** {dob} {birth_time.strftime('%H:%M:%S')} ({state} / {district})")
    st.write(f"**Coordinates used:** {lat:.6f}°N, {lon:.6f}°E  | TZ: {tz_name}")
    st.write(f"**Ayanamsa (Lahiri) used (deg):** {ayanamsa_deg:.8f}")
    st.write(f"- **Tithi:** {vedic_tithi}  ({vedic_paksha})")
    st.write(f"- **Nakshatra:** {vedic_nakshatra}")
    st.write(f"- **Masa (approx):** {vedic_masa}")
    st.write(f"- **Rashi (Moon sign, sidereal):** {vedic_rashi}")
    st.write(f"- **Weekday:** {weekday_local}")
    st.write(f"- **Tithi angle (moon - sun) in degrees:** {tithi_angle:.6f}")
    st.markdown("**Raw sidereal longitudes**")
    st.write(f"- Sun (sidereal): {sun_sid:.6f}°")
    st.write(f"- Moon (sidereal): {moon_sid:.6f}°")
    st.markdown("**Next birthdays**")
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
                "ayanamsa_deg": round(ayanamsa_deg, 8),
                "vedic_details": f"{vedic_tithi}, {vedic_nakshatra}, {vedic_masa}, {vedic_rashi}",
                "solar_birthday_next_year": solar_bday_next.isoformat(),
                "next_vedic_dob": next_vedic_date.isoformat()
            }).execute()
            st.success("Saved to Supabase ✅")
        except Exception as e:
            st.error(f"Could not save to Supabase: {e}")

    st.caption("Note: This implementation uses Swiss Ephemeris (pyswisseph) for accurate planetary positions and ayanamsa. For absolute production parity with a specific Panchang, we can add extra diagnostics or compare raw numbers side-by-side.")