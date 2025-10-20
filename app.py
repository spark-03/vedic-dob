# app.py
import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta, time as dtime
import ephem
import math
import pytz

st.set_page_config(page_title="Vedic DOB Finder (Sidereal/Lahiri)", layout="centered")
st.title("📿 Vedic DOB Finder — Sidereal (Lahiri)")

# -----------------------
# Supabase setup (Streamlit secrets)
# -----------------------
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None
    st.info("Supabase not configured. Add Streamlit secrets to save records.")

# -----------------------
# Sample district-level coordinates (extend as needed)
# -----------------------
location_data = {
    "Andhra Pradesh": {
        "Anantapur": {"lat": 14.6816, "lon": 77.6003, "tz": "Asia/Kolkata"},
        "Chittoor": {"lat": 13.2172, "lon": 79.1003, "tz": "Asia/Kolkata"},
        "Guntur": {"lat": 16.3067, "lon": 80.4365, "tz": "Asia/Kolkata"},
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
    },
    "Telangana": {
        "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "tz": "Asia/Kolkata"},
        "Warangal": {"lat": 17.9789, "lon": 79.5916, "tz": "Asia/Kolkata"},
    },
    "Tamil Nadu": {
        "Chennai": {"lat": 13.0827, "lon": 80.2707, "tz": "Asia/Kolkata"},
        "Madurai": {"lat": 9.9252, "lon": 78.1198, "tz": "Asia/Kolkata"},
        "Coimbatore": {"lat": 11.0168, "lon": 76.9558, "tz": "Asia/Kolkata"},
    },
    "Karnataka": {
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "tz": "Asia/Kolkata"},
        "Mysuru": {"lat": 12.2958, "lon": 76.6394, "tz": "Asia/Kolkata"},
    },
    "Kerala": {
        "Thiruvananthapuram": {"lat": 8.5241, "lon": 76.9366, "tz": "Asia/Kolkata"},
        "Kochi": {"lat": 9.9312, "lon": 76.2673, "tz": "Asia/Kolkata"},
    },
    "Maharashtra": {
        "Mumbai": {"lat": 19.0760, "lon": 72.8777, "tz": "Asia/Kolkata"},
        "Pune": {"lat": 18.5204, "lon": 73.8567, "tz": "Asia/Kolkata"},
    },
    "Delhi": {
        "New Delhi": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    },
    "West Bengal": {
        "Kolkata": {"lat": 22.5726, "lon": 88.3639, "tz": "Asia/Kolkata"},
    },
    "Bihar": {
        "Patna": {"lat": 25.5941, "lon": 85.1376, "tz": "Asia/Kolkata"},
    },
    "Punjab": {
        "Amritsar": {"lat": 31.6340, "lon": 74.8723, "tz": "Asia/Kolkata"},
    },
    # Add more states/districts as needed
}

# -----------------------
# UI: Inputs (form)
# -----------------------
with st.form("birth_form"):
    name = st.text_input("Full name")
    dob = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today())
    birth_time = st.time_input("Time of birth (local)", value=dtime(6, 0))
    st.markdown("Select place of birth (state → district). District coordinates are representative — add more for finer accuracy.")
    state = st.selectbox("State", sorted(location_data.keys()))
    district = st.selectbox("District", sorted(location_data[state].keys()))
    submit = st.form_submit_button("Calculate Vedic DOB")

if not submit:
    st.caption("Enter details and press Calculate.")
else:
    # place info
    place = location_data[state][district]
    lat = place["lat"]
    lon = place["lon"]
    tz_name = place.get("tz", "Asia/Kolkata")

    # timezone objects
    try:
        local_tz = pytz.timezone(tz_name)
    except Exception:
        local_tz = pytz.timezone("UTC")

    # local datetime -> UTC
    local_dt = datetime.combine(dob, birth_time)
    local_dt = local_tz.localize(local_dt)
    utc_dt = local_dt.astimezone(pytz.utc)

    # helper: build ephem observer at location/time (UTC)
    def build_observer_for_utc(utc_dt, lat, lon):
        obs = ephem.Observer()
        obs.lat = str(lat)
        obs.lon = str(lon)
        obs.date = utc_dt.strftime("%Y/%m/%d %H:%M:%S")
        return obs

    # compute geocentric ecliptic longitudes for Sun & Moon (degrees)
    def sun_moon_ecliptic(utc_dt, lat, lon):
        obs = build_observer_for_utc(utc_dt, lat, lon)
        sun = ephem.Sun(obs)
        moon = ephem.Moon(obs)
        sun_ecl = ephem.Ecliptic(sun)
        moon_ecl = ephem.Ecliptic(moon)
        sun_lon = math.degrees(sun_ecl.lon) % 360
        moon_lon = math.degrees(moon_ecl.lon) % 360
        return sun_lon, moon_lon

    # compute Julian Day (for ayanamsa calc)
    def julian_day_from_utc(utc_dt):
        obs = ephem.Observer()
        obs.date = utc_dt.strftime("%Y/%m/%d %H:%M:%S")
        return float(ephem.julian_date(obs.date))

    # approximate Lahiri ayanamsa (linear approx in degrees from J2000)
    # NOTE: this is an approximation. For production use, use pyswisseph for precise ayanamsa.
    def lahiri_ayanamsa_deg(utc_dt):
        jd = julian_day_from_utc(utc_dt)
        years_since_j2000 = (jd - 2451545.0) / 365.25
        # base at J2000 ~ 23.843 degrees (approx). rate ~ 0.013968 deg/year (approx)
        base_deg = 23.843  # approx Lahiri around 2000 (deg)
        rate_deg_per_year = 0.013968  # approx precession-based rate deg/year
        ay_deg = base_deg + rate_deg_per_year * years_since_j2000
        return ay_deg

    # convert tropical ecliptic longitude -> sidereal by subtracting ayanamsa
    def to_sidereal(tropical_deg, ay_deg):
        sid = (tropical_deg - ay_deg) % 360
        return sid

    # Panchang element calculators (using sidereal longitudes)
    def get_sidereal_sun_moon(utc_dt):
        sun_trop, moon_trop = sun_moon_ecliptic(utc_dt, lat, lon)
        ay = lahiri_ayanamsa_deg(utc_dt)
        sun_sid = to_sidereal(sun_trop, ay)
        moon_sid = to_sidereal(moon_trop, ay)
        return sun_sid, moon_sid, ay

    def get_tithi_num_from_sidereal(utc_dt):
        sun_sid, moon_sid, _ = get_sidereal_sun_moon(utc_dt)
        diff = (moon_sid - sun_sid) % 360
        tnum = int(diff / 12) + 1  # 1..30
        return tnum

    def tithi_name_from_num(tnum):
        tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
                  "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
                  "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
        if tnum <= 15:
            return f"Shukla {tithis[tnum - 1]}"
        else:
            return f"Krishna {tithis[(tnum - 16) % 15]}"

    def get_nakshatra_from_sidereal(utc_dt):
        _, moon_sid, _ = get_sidereal_sun_moon(utc_dt)
        idx = int((moon_sid % 360) / (360.0 / 27.0))
        naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
        return naks[idx]

    def get_rashi_from_sidereal(utc_dt):
        _, moon_sid, _ = get_sidereal_sun_moon(utc_dt)
        ridx = int(moon_sid / 30) % 12
        rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
                  "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
        return rashis[ridx]

    def get_masa_from_sidereal(utc_dt):
        # approximate masa: derive from sidereal sun longitude mapping to month names
        sun_sid, _, _ = get_sidereal_sun_moon(utc_dt)
        lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                        "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                        "Magha", "Phalguna"]
        m_idx = int((sun_sid + 30) / 30) % 12
        return lunar_months[m_idx]

    # Compute Vedic elements at birth instant
    birth_utc = utc_dt
    tithi_num = get_tithi_num_from_sidereal(birth_utc)
    vedic_tithi = tithi_name_from_num(tithi_num)
    vedic_nakshatra = get_nakshatra_from_sidereal(birth_utc)
    vedic_rashi = get_rashi_from_sidereal(birth_utc)
    vedic_masa = get_masa_from_sidereal(birth_utc)
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    weekday = local_dt.strftime("%A")
    ayanamsa_used = lahiri_ayanamsa_deg(birth_utc)

    # -----------------------
    # Find next exact Vedic date (match all sidereal elements)
    # -----------------------
    def find_next_exact_vedic(local_dt_localized, max_days=450):
        # start from same solar date next year (local), then iterate
        try:
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1)
        except ValueError:
            start_local = local_dt_localized.replace(year=local_dt_localized.year + 1, month=1, day=1)

        for i in range(max_days):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            c_t = get_tithi_num_from_sidereal(cand_utc)
            c_masa = get_masa_from_sidereal(cand_utc)
            c_nak = get_nakshatra_from_sidereal(cand_utc)
            c_rash = get_rashi_from_sidereal(cand_utc)
            if c_t == tithi_num and c_masa == vedic_masa and c_nak == vedic_nakshatra and c_rash == vedic_rashi:
                return cand_local.date()
        # fallback: match tithi+masa
        for i in range(365):
            cand_local = start_local + timedelta(days=i)
            cand_utc = cand_local.astimezone(pytz.utc)
            c_t = get_tithi_num_from_sidereal(cand_utc)
            c_masa = get_masa_from_sidereal(cand_utc)
            if c_t == tithi_num and c_masa == vedic_masa:
                return cand_local.date()
        return start_local.date()

    # find next vedic date
    dob_localized = local_tz.localize(datetime.combine(dob, birth_time))
    solar_bday_next_year = None
    try:
        solar_bday_next_year = dob_localized.replace(year=dob_localized.year + 1).date()
    except Exception:
        solar_bday_next_year = date(dob.year + 1, 1, 1)

    next_vedic_date = find_next_exact_vedic(dob_localized)

    # -----------------------
    # Output results
    # -----------------------
    st.markdown("### ✅ Computed Vedic Details (Sidereal — Lahiri approx.)")
    st.write(f"**Name:** {name}")
    st.write(f"**Birth (local):** {dob} {birth_time.strftime('%H:%M')} ({state} / {district})")
    st.write(f"**Coordinates used:** {lat:.4f}°N, {lon:.4f}°E — timezone {tz_name}")
    st.write(f"**Ayanamsa used (approx):** {ayanamsa_used:.4f}° (Lahiri approx.)")
    st.write(f"- **Tithi:** {vedic_tithi} ({paksha})")
    st.write(f"- **Nakshatra:** {vedic_nakshatra}")
    st.write(f"- **Masa (approx):** {vedic_masa}")
    st.write(f"- **Rashi (Moon sign, sidereal):** {vedic_rashi}")
    st.write(f"- **Weekday:** {weekday}")
    st.markdown("**Next birthdays:**")
    st.write(f"- Solar birthday next year: **{solar_bday_next_year}**")
    st.write(f"- Next exact Vedic DOB (match Tithi+Masa+Nakshatra+Rashi): **{next_vedic_date}**")

    # -----------------------
    # Save to Supabase if configured
    # -----------------------
    if supabase:
        try:
            supabase.table("users").insert({
                "name": name,
                "dob": dob.isoformat(),
                "time_of_birth": birth_time.strftime("%H:%M"),
                "state": state,
                "district": district,
                "lat": lat,
                "lon": lon,
                "ayanamsa_deg": round(ayanamsa_used, 6),
                "vedic_details": f"{vedic_tithi}, {vedic_nakshatra}, {vedic_masa}, {vedic_rashi}, {weekday}",
                "solar_birthday_next_year": solar_bday_next_year.isoformat(),
                "next_vedic_dob": next_vedic_date.isoformat()
            }).execute()
            st.success("Saved to Supabase ✅")
        except Exception as e:
            st.error(f"Could not save to Supabase: {e}")

    st.caption("Note: This uses an approximate Lahiri ayanamsa. For highest precision use pyswisseph (Swiss Ephemeris) to compute ayanamsa and planetary longitudes.")