import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import pytz
import swisseph as swe
from supabase import create_client

st.set_page_config(page_title="Vedic DOB Finder", layout="centered")
st.title("📿 Vedic DOB Finder — Swiss Ephemeris (Lahiri)")

# Optional Supabase setup
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# Coordinates (district-level)
location_data = {
    "Andhra Pradesh": {
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
    },
    "Telangana": {"Hyderabad": {"lat": 17.3850, "lon": 78.4867, "tz": "Asia/Kolkata"}},
}

# Set Lahiri mode
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

# Helpers
def jd_from_utc_dt(utc_dt: datetime) -> float:
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

def sun_moon_sidereal_topo(jd_ut: float, lon: float, lat: float, height: float = 0.0):
    swe.set_topo(lon, lat, height)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR
    sun = swe.calc_ut(jd_ut, swe.SUN, flags)[0] % 360
    moon = swe.calc_ut(jd_ut, swe.MOON, flags)[0] % 360
    return sun, moon

def tithi_num_from_sidereal(sun_sid: float, moon_sid: float) -> int:
    diff = (moon_sid - sun_sid) % 360
    return int(diff // 12) + 1  # 1..30

def tithi_name_from_num(tnum: int) -> str:
    tithis = [
        "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
        "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
        "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
    ]
    if 1 <= tnum <= 15:
        return "Shukla " + tithis[tnum - 1]
    else:
        return "Krishna " + tithis[(tnum - 16) % 15]

def nakshatra_from_sidereal(moon_sid: float):
    idx = int((moon_sid % 360) // (360 / 27))
    names = [
        "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu",
        "Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta",
        "Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha",
        "Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
        "Uttara Bhadrapada","Revati"
    ]
    return names[idx], idx, (moon_sid % 360) - idx * (360 / 27)

def rashi_from_sidereal(moon_sid: float):
    idx = int(moon_sid // 30)
    rashis = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika",
              "Dhanu","Makara","Kumbha","Meena"]
    return rashis[idx], idx, moon_sid - idx * 30

def masa_from_sidereal(sun_sid: float):
    months = ["Chaitra","Vaishakha","Jyeshtha","Ashadha","Shravana","Bhadrapada",
              "Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]
    return months[int((sun_sid + 30) // 30) % 12]

# Input Form
with st.form("birth"):
    name = st.text_input("Full name")
    dob = st.date_input("Date of birth", min_value=date(1900, 1, 1))
    birth_time = st.time_input("Time of birth (local)", value=dtime(0, 0))
    state = st.selectbox("State", sorted(location_data.keys()))
    district = st.selectbox("District", sorted(location_data[state].keys()))
    submit = st.form_submit_button("Calculate")

if submit:
    lat = location_data[state][district]["lat"]
    lon = location_data[state][district]["lon"]
    tz = pytz.timezone(location_data[state][district]["tz"])

    local_dt = tz.localize(datetime.combine(dob, birth_time))
    utc_dt = local_dt.astimezone(pytz.utc)
    jd_ut = jd_from_utc_dt(utc_dt)

    sun_sid, moon_sid = sun_moon_sidereal_topo(jd_ut, lon, lat)
    tnum = tithi_num_from_sidereal(sun_sid, moon_sid)
    tithi = tithi_name_from_num(tnum)
    nak, _, _ = nakshatra_from_sidereal(moon_sid)
    masa = masa_from_sidereal(sun_sid)
    rashi, _, _ = rashi_from_sidereal(moon_sid)
    paksha = "Shukla" if tnum <= 15 else "Krishna"
    weekday = local_dt.strftime("%A")

    st.markdown("### ✅ Vedic Birth Details")
    st.write(f"**Name:** {name}")
    st.write(f"**Date (local):** {local_dt}")
    st.write(f"**Tithi:** {tithi} ({paksha})")
    st.write(f"**Nakshatra:** {nak}")
    st.write(f"**Masa:** {masa}")
    st.write(f"**Rashi:** {rashi}")
    st.write(f"**Weekday:** {weekday}")