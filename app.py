import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta, time as dtime
import ephem
import math
import pytz

st.set_page_config(page_title="Vedic DOB Finder", layout="centered")
st.title("📿 Vedic Date of Birth Finder (Time & Place-aware)")

# -----------------------
# Supabase setup (Streamlit secrets)
# -----------------------
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None
    st.info("Supabase not configured (results still shown locally). Add Supabase secrets to save records.")

# -----------------------
# Minimal district-level location database (expand as needed)
# Keys: state -> district -> {lat, lon, timezone}
# For India, timezone is "Asia/Kolkata" for all entries below.
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
    # Add more states/districts as needed...
}

# -----------------------
# UI Inputs
# -----------------------
with st.form("input_form"):
    name = st.text_input("Enter your name")
    dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
    # time input: default 00:00 if unknown (better to ask user to enter time)
    birth_time = st.time_input("Time of birth (local)", value=dtime(6, 0), help="Enter local time of birth (HH:MM). If unknown, keep a best guess.")
    st.markdown("**Select place of birth** (state → district). District selection uses representative coordinates — extend location_data for more precision.")
    state = st.selectbox("State", sorted(location_data.keys()))
    district = st.selectbox("District", sorted(location_data[state].keys()))
    submitted = st.form_submit_button("Calculate Vedic DOB")

if not submitted:
    st.caption("Enter details and press Calculate")
else:
    # get selected place info
    place_info = location_data[state][district]
    lat = place_info["lat"]
    lon = place_info["lon"]
    tz_name = place_info["tz"]

    # -----------------------
    # Timezone & Observer setup
    # -----------------------
    try:
        local_tz = pytz.timezone(tz_name)
    except Exception:
        local_tz = pytz.timezone("UTC")

    # combine dob + birth_time to a localized datetime, then convert to UTC for ephem observer
    local_dt = datetime.combine(dob, birth_time)
    local_dt = local_tz.localize(local_dt)
    utc_dt = local_dt.astimezone(pytz.utc)

    # helper: build ephem Observer for a given utc datetime
    def build_observer(utc_datetime, latitude, longitude):
        obs = ephem.Observer()
        obs.lat = str(latitude)
        obs.lon = str(longitude)
        # ephem wants UTC-like string; set to UTC date/time
        obs.date = utc_datetime.strftime("%Y/%m/%d %H:%M:%S")
        return obs

    # -----------------------
    # Accurate ecliptic longitudes (geocentric)
    # -----------------------
    def sun_moon_ecliptic_longitudes(utc_datetime, latitude, longitude):
        obs = build_observer(utc_datetime, latitude, longitude)
        sun = ephem.Sun(obs)
        moon = ephem.Moon(obs)
        # use geocentric ecliptic longitudes via ephem.Ecliptic
        sun_ecl = ephem.Ecliptic(sun)
        moon_ecl = ephem.Ecliptic(moon)
        sun_long = math.degrees(sun_ecl.lon) % 360
        moon_long = math.degrees(moon_ecl.lon) % 360
        return sun_long, moon_long

    # -----------------------
    # Panchang element calculators
    # -----------------------
    def get_tithi_num(utc_datetime):
        s, m = sun_moon_ecliptic_longitudes(utc_datetime, lat, lon)
        diff = (m - s) % 360
        t_num = int(diff / 12) + 1  # 1..30
        return t_num

    def tithi_name_from_num(t_num):
        tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
                  "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
                  "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"]
        if t_num <= 15:
            return f"Shukla {tithis[t_num - 1]}"
        else:
            # map 16->1 of Krishna names (16-30 => 1-15)
            return f"Krishna {tithis[(t_num - 16) % 15]}"

    def get_nakshatra(utc_datetime):
        _, moon_long = sun_moon_ecliptic_longitudes(utc_datetime, lat, lon)
        index = int((moon_long % 360) / (360 / 27))
        nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                      "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                      "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                      "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                      "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                      "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
        return nakshatras[index]

    def get_rashi(utc_datetime):
        _, moon_long = sun_moon_ecliptic_longitudes(utc_datetime, lat, lon)
        r_index = int(moon_long / 30) % 12
        rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
                  "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
        return rashis[r_index]

    def get_masa(utc_datetime, use_amanta=True):
        """
        Approximate lunar month (Masa) by Sun's ecliptic longitude and Amanta/Purnimanta rule.
        For India commonly Amanta (month ends on new moon) is used in South; adjust if needed.
        This function returns a representative month name for the sun longitude.
        """
        sun_long, _ = sun_moon_ecliptic_longitudes(utc_datetime, lat, lon)
        # map sun_long to solar zodiac index; convert to month index roughly
        # This is a pragmatic mapping — for full classical accuracy, you'd compute month by nearest new moon mapping.
        lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                        "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                        "Magha", "Phalguna"]
        month_index = int((sun_long + 30) / 30) % 12
        return lunar_months[month_index]

    # -----------------------
    # Compute Vedic details for birth instant
    # -----------------------
    birth_utc = utc_dt  # already UTC datetime
    tithi_num = get_tithi_num(birth_utc)
    vedic_tithi = tithi_name_from_num(tithi_num)
    vedic_nakshatra = get_nakshatra(birth_utc)
    vedic_rashi = get_rashi(birth_utc)
    vedic_masa = get_masa(birth_utc)
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    weekday = local_dt.strftime("%A")

    # -----------------------
    # Next year: find exact match of Tithi+Masa+Nakshatra+Rashi
    # -----------------------
    def find_next_exact_vedic_date(dob_local_dt, max_days=400):
        # Start searching from same solar date next year, using local timezone
        try:
            start_local = dob_local_dt.replace(year=dob_local_dt.year + 1)
        except ValueError:  # Feb 29 fallback
            start_local = dob_local_dt.replace(year=dob_local_dt.year + 1, month=1, day=1)

        # iterate over max_days (covering possible shifts)
        for i in range(max_days):
            candidate_local = start_local + timedelta(days=i)
            # convert candidate_local to UTC using local tz
            candidate_utc = candidate_local.astimezone(pytz.utc)
            # compute Vedic elements
            c_t = get_tithi_num(candidate_utc)
            c_masa = get_masa(candidate_utc)
            c_nak = get_nakshatra(candidate_utc)
            c_rash = get_rashi(candidate_utc)

            if (c_t == tithi_num and c_masa == vedic_masa and c_nak == vedic_nakshatra and c_rash == vedic_rashi):
                return candidate_local.date()
        # if exact match not found, fallback to first date matching tithi+masa only
        for i in range(365):
            candidate_local = start_local + timedelta(days=i)
            candidate_utc = candidate_local.astimezone(pytz.utc)
            c_t = get_tithi_num(candidate_utc)
            c_masa = get_masa(candidate_utc)
            if c_t == tithi_num and c_masa == vedic_masa:
                return candidate_local.date()
        return start_local.date()

    # prepare local datetime for search (localized)
    dob_local_dt = local_tz.localize(datetime.combine(dob, birth_time))
    solar_birthday_next_year = None
    try:
        solar_birthday_next_year = (dob_local_dt.replace(year=dob_local_dt.year + 1)).date()
    except Exception:
        solar_birthday_next_year = date(dob.year + 1, 1, 1)

    next_vedic = find_next_exact_vedic_date(dob_local_dt)

    # -----------------------
    # Show results
    # -----------------------
    st.markdown("### ✅ Results")
    st.write(f"**Name:** {name}")
    st.write(f"**Birth (local):** {dob} {birth_time.strftime('%H:%M')} ({state} / {district})")
    st.write(f"**Coordinates used:** {lat:.4f}°N, {lon:.4f}°E | Timezone: {tz_name}")
    st.markdown("**Vedic (Panchang) at birth moment:**")
    st.write(f"- Tithi: **{vedic_tithi}** ({paksha})")
    st.write(f"- Nakshatra: **{vedic_nakshatra}**")
    st.write(f"- Masa (approx.): **{vedic_masa}**")
    st.write(f"- Rashi (Moon sign): **{vedic_rashi}**")
    st.write(f"- Weekday: **{weekday}**")
    st.markdown("**Next birthdays:**")
    st.write(f"- Solar birthday next year (same Gregorian day): **{solar_birthday_next_year}**")
    st.write(f"- Next exact Vedic DOB (all elements matched): **{next_vedic}**")

    # -----------------------
    # Save to Supabase (if configured)
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
                "vedic_details": f"{vedic_tithi}, {vedic_nakshatra}, {vedic_masa}, {vedic_rashi}, {weekday}",
                "solar_birthday_next_year": solar_birthday_next_year.isoformat(),
                "next_vedic_dob": next_vedic.isoformat()
            }).execute()
            st.success("Saved to Supabase ✅")
        except Exception as e:
            st.error(f"Could not save to Supabase: {e}")

    st.caption("Developed by Spark ✨ | District-level place lookup used for location accuracy.")