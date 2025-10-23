# app.py — Modern UI Vedic DOB (Swiss Ephemeris sidereal Lahiri + topocentric)
import streamlit as st
from datetime import date, datetime, timedelta, time as dtime
import pytz
import swisseph as swe
import math
from supabase import create_client

# -----------------------
# Config / minimal district data (extend this dict as you like)
# Each district is {lat, lon, tz}
# -----------------------
DISTRICT_DATA = {
    "Andhra Pradesh": {
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
        "Vijayawada": {"lat": 16.5062, "lon": 80.6480, "tz": "Asia/Kolkata"},
        "Tirupati": {"lat": 13.6288, "lon": 79.4192, "tz": "Asia/Kolkata"},
    },
    "Telangana": {
        "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "tz": "Asia/Kolkata"},
        "Warangal": {"lat": 17.9789, "lon": 79.5916, "tz": "Asia/Kolkata"},
    },
    "Tamil Nadu": {
        "Chennai": {"lat": 13.0827, "lon": 80.2707, "tz": "Asia/Kolkata"},
        "Madurai": {"lat": 9.9252, "lon": 78.1198, "tz": "Asia/Kolkata"},
    },
    "Karnataka": {
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"},
        "Mysuru": {"lat": 12.2958, "lon": 76.6394, "tz": "Asia/Kolkata"},
    },
    "Maharashtra": {
        "Mumbai": {"lat": 19.0760, "lon": 72.8777, "tz": "Asia/Kolkata"},
        "Pune": {"lat": 18.5204, "lon": 73.8567, "tz": "Asia/Kolkata"},
    },
    "Delhi": {"New Delhi": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}},
    # Add more states/districts as needed
}

# -----------------------
# Swiss Ephemeris init
# Use Lahiri sidereal mode
# -----------------------
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

# -----------------------
# Supabase (optional) - read from streamlit secrets
# -----------------------
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# -----------------------
# Utility functions
# -----------------------
def jd_from_utc(dt_utc: datetime) -> float:
    """Return Julian Day (UT) for a timezone-aware UTC datetime."""
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    hour_decimal = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(y, m, d, hour_decimal)

def sun_moon_sidereal_topo(jd_ut: float, lon_deg: float, lat_deg: float, height_m: float = 0.0):
    """
    Compute topocentric sidereal longitudes (Lahiri) of Sun and Moon using Swiss Ephemeris.
    Returns (sun_sid_deg, moon_sid_deg, ayanamsa_deg)
    """
    # set topo (lon, lat, height) for topocentric correction
    swe.set_topo(lon_deg, lat_deg, height_m)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR
    # calc_ut returns tuple (result, retflag) in many builds; result is array-like [lon, lat, dist, ...]
    sun_res, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon_res, _ = swe.calc_ut(jd_ut, swe.MOON, flags)
    # get ayanamsa for diagnostics
    try:
        ay = swe.get_ayanamsa(jd_ut)
    except Exception:
        ay = swe.get_ayanamsa_ut(jd_ut) if hasattr(swe, "get_ayanamsa_ut") else 0.0
    sun_sid = float(sun_res[0]) % 360
    moon_sid = float(moon_res[0]) % 360
    return sun_sid, moon_sid, float(ay)

def tithi_from_sidereal(sun_sid: float, moon_sid: float):
    """Return tithi number (1..30) and name + paksha"""
    diff = (moon_sid - sun_sid) % 360
    tnum = int(diff // 12) + 1
    paksha = "Shukla" if tnum <= 15 else "Krishna"
    tithis = ["Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
              "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
    tname = tithis[(tnum - 1) % 15]
    return tnum, f"{paksha} {tname}", paksha, diff  # include angle diff for diagnostics

def nakshatra_from_sidereal(moon_sid: float):
    """Return nakshatra name, index (1..27), degrees into nakshatra, and pada (1..4)"""
    sector = 360.0 / 27.0
    idx0 = int((moon_sid % 360) // sector)  # 0..26
    deg_into = (moon_sid % 360) - idx0 * sector
    pada = int(deg_into // (sector / 4)) + 1
    names = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
             "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
             "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
             "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
             "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
             "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return names[idx0], idx0 + 1, deg_into, pada

def rashi_from_sidereal(moon_sid: float):
    """Return Rashi (Moon Sign) name, index 1..12, degrees into rashi"""
    idx = int((moon_sid % 360) // 30)
    deg_into = (moon_sid % 360) - idx * 30
    names = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
             "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return names[idx], idx + 1, deg_into

# --- NEW FUNCTION FOR SUN RASHI ---
def rashi_from_sidereal_sun(sun_sid: float):
    """Return Rashi (Sun Sign) name, index 1..12, degrees into rashi"""
    idx = int((sun_sid % 360) // 30)
    deg_into = (sun_sid % 360) - idx * 30
    names = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
             "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return names[idx], idx + 1, deg_into
# ----------------------------------

def masa_from_sidereal(sun_sid: float):
    """Approximate lunar month name from sidereal sun (Amanta-style approx)."""
    idx = int(((sun_sid + 30) % 360) // 30)
    months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
              "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
              "Magha", "Phalguna"]
    return months[idx]

# -----------------------
# Streamlit UI (modern look)
# -----------------------
st.set_page_config(page_title="Vedic DOB — Modern UI", layout="centered")
st.markdown("<h1 style='text-align:center'>📿 Vedic DOB — Accurate & Fast</h1>", unsafe_allow_html=True)
st.write("Enter birth details. Results use topocentric sidereal positions (Lahiri) for high accuracy.")

# left column: inputs; right column: results
col1, col2 = st.columns([1, 1])

with col1:
    with st.form("input_form"):
        name = st.text_input("Full name")
        dob = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today())
        birth_time = st.time_input("Time of birth (local)", value=dtime(6, 0))
        st.markdown("**Place of birth**")
        state = st.selectbox("State", sorted(DISTRICT_DATA.keys()))
        district = st.selectbox("District", sorted(DISTRICT_DATA[state].keys()))
        manual = st.checkbox("Manual lat/lon override", value=False)
        if manual:
            lat = st.number_input("Latitude (deg, north +)", value=float(DISTRICT_DATA[state][district]["lat"]))
            lon = st.number_input("Longitude (deg, east +)", value=float(DISTRICT_DATA[state][district]["lon"]))
            tz_name = st.text_input("Timezone (IANA)", value=DISTRICT_DATA[state][district]["tz"])
        else:
            lat = DISTRICT_DATA[state][district]["lat"]
            lon = DISTRICT_DATA[state][district]["lon"]
            tz_name = DISTRICT_DATA[state][district]["tz"]
        submit = st.form_submit_button("Calculate Vedic DOB")

with col2:
    st.empty()  # placeholder for results

# handle submit
if submit:
    # localize time and compute JD UT
    try:
        local_tz = pytz.timezone(tz_name)
    except Exception:
        st.warning("Invalid timezone; defaulting to Asia/Kolkata")
        local_tz = pytz.timezone("Asia/Kolkata")

    local_dt = local_tz.localize(datetime.combine(dob, birth_time))
    utc_dt = local_dt.astimezone(pytz.utc)
    jd_ut = jd_from_utc(utc_dt)

    # compute sidereal topocentric sun/moon and ayanamsa
    with st.spinner("Computing accurate sidereal positions..."):
        try:
            sun_sid, moon_sid, ay_deg = sun_moon_sidereal_topo(jd_ut, lon, lat, 0.0)
        except Exception as e:
            st.error(f"Error from Swiss Ephemeris: {e}")
            st.stop()

    # derive panchang elements
    tnum, tname, paksha, tangle = tithi_from_sidereal(sun_sid, moon_sid)
    nak_name, nak_idx, nak_deg, nak_pada = nakshatra_from_sidereal(moon_sid)
    rashi_name, rashi_idx, rashi_deg = rashi_from_sidereal(moon_sid) # Moon Rashi
    sun_rashi_name, sun_rashi_idx, sun_rashi_deg = rashi_from_sidereal_sun(sun_sid) # --- NEW: Sun Rashi ---
    masa_name = masa_from_sidereal(sun_sid)
    weekday = local_dt.strftime("%A")

    # show results: modern UI cards/metrics
    st.experimental_rerun() if False else None  # keeps layout stable

    # Results header
    st.markdown("---")
    st.markdown(f"## ✨ Results for **{name or '—'}**")
    st.markdown(f"**Birth (local):** {local_dt.strftime('%Y-%m-%d %H:%M:%S')} — `{state} / {district}`")
    st.markdown("---")

    # cards: three columns
    c1, c2, c3 = st.columns(3)
    c1.metric(label="Tithi", value=f"{tname} (#{tnum})", delta=f"{paksha}")
    c2.metric(label="Rashi (Moon sign)", value=f"{rashi_name}", delta=f"{rashi_deg:.2f}° into sign")
    c3.metric(label="Nakshatra", value=f"{nak_name}", delta=f"Pada {nak_pada}")

    # second row: masa, weekday, sun sign, next solar
    c4, c5, c6 = st.columns(3)
    c4.metric(label="Masa (approx.)", value=masa_name)
    c5.metric(label="Weekday", value=weekday)
    c6.metric(label="Rashi (Sun sign)", value=f"{sun_rashi_name}", delta=f"{sun_rashi_deg:.2f}° into sign") # --- NEW METRIC ---
    
    # solar birthday next year - put this below for a cleaner layout
    st.markdown("---")
    st.subheader("Next Significant Dates")
    c7, c8 = st.columns(2)
    try:
        solar_next = local_dt.replace(year=local_dt.year + 1).date()
    except Exception:
        solar_next = date(local_dt.year + 1, 1, 1)
    c7.metric(label="Solar birthday (next year)", value=str(solar_next))

    # diagnostics & raw numbers
    with st.expander("Diagnostics & Raw numbers (click to open)"):
        st.write(f"Ayanamsa (Lahiri) used: **{ay_deg:.6f}°**")
        st.write(f"Sun (sidereal) : {sun_sid:.6f}°")
        st.write(f"Moon (sidereal): {moon_sid:.6f}°")
        st.write(f"Tithi angle (Moon - Sun): {tangle:.6f}°")
        st.write(f"Nakshatra #{nak_idx} — {nak_deg:.6f}° into nakshatra")
        st.write(f"Moon Rashi idx: {rashi_idx} (1..12), {rashi_deg:.6f}° into rashi")
        st.write(f"**Sun Rashi idx**: {sun_rashi_idx} (1..12), **{sun_rashi_deg:.6f}°** into rashi") # --- NEW DIAGNOSTIC ---
        st.write("Coordinates used:", f"{lat:.6f}°N, {lon:.6f}°E")
        st.write("Local timezone:", tz_name)

    # find next exact vedic date (match Tithi+Masa+Nakshatra+Rashi)
    with st.spinner("Searching for next exact Vedic DOB (can take a few seconds)..."):
        def find_next_vedic(local_dt_localized, max_days=450):
            try:
                start = local_dt_localized.replace(year=local_dt_localized.year + 1)
            except Exception:
                start = local_dt_localized.replace(year=local_dt_localized.year + 1, month=1, day=1)
            for i in range(max_days):
                cand_local = start + timedelta(days=i)
                cand_utc = cand_local.astimezone(pytz.utc)
                jd_c = jd_from_utc(cand_utc)
                try:
                    s_c, m_c, _ = sun_moon_sidereal_topo(jd_c, lon, lat, 0.0)
                except Exception:
                    continue
                tnum_c, tname_c, _, _ = tithi_from_sidereal(s_c, m_c)
                nak_c, _, _, _ = nakshatra_from_sidereal(m_c)
                rashi_c, _, _ = rashi_from_sidereal(m_c)
                masa_c = masa_from_sidereal(s_c)
                if (tnum_c == tnum and nak_c == nak_name and rashi_c == rashi_name and masa_c == masa_name):
                    return cand_local.date()
            # fallback: match tithi+masa only
            for i in range(365):
                cand_local = start + timedelta(days=i)
                cand_utc = cand_local.astimezone(pytz.utc)
                jd_c = jd_from_utc(cand_utc)
                try:
                    s_c, m_c, _ = sun_moon_sidereal_topo(jd_c, lon, lat, 0.0)
                except Exception:
                    continue
                if tithi_from_sidereal(s_c, m_c)[0] == tnum and masa_from_sidereal(s_c) == masa_name:
                    return cand_local.date()
            return start.date()

        next_vedic = find_next_vedic(local_dt)

    c8.metric(label="Next Vedic birthday (Tithi+Nak+Rashi)", value=str(next_vedic))


    # Save to Supabase (optional)
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
                "vedic_tithi": tname,
                "vedic_paksha": paksha,
                "vedic_nakshatra": nak_name,
                "vedic_nakshatra_pada": nak_pada,
                "vedic_masa": masa_name,
                "vedic_rashi": rashi_name,
                "vedic_sun_rashi": sun_rashi_name, # --- NEW FIELD ---
                "solar_birthday_next_year": solar_next.isoformat(),
                "next_vedic_dob": str(next_vedic)
            }).execute()
            st.success("Saved to Supabase ✅")
        except Exception as e:
            st.error(f"Could not save to Supabase: {e}")

st.markdown("---")
st.caption("Modern UI · Topocentric sidereal calculations (Lahiri) · Expand diagnostics for raw numbers. Add more districts in DISTRICT_DATA for coverage.")
