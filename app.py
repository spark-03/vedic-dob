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
        # Coastal Andhra
        "Srikakulam": {"lat": 18.2974, "lon": 83.8970, "tz": "Asia/Kolkata"},
        "Parvathipuram Manyam": {"lat": 18.7845, "lon": 83.4116, "tz": "Asia/Kolkata"},
        "Vizianagaram": {"lat": 18.1170, "lon": 83.3934, "tz": "Asia/Kolkata"},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"},
        "Alluri Sitharama Raju": {"lat": 17.6868, "lon": 83.2185, "tz": "Asia/Kolkata"}, # Placeholder: Same as Vizag city for now
        "Anakapalli": {"lat": 17.7011, "lon": 83.0035, "tz": "Asia/Kolkata"},
        "Kakinada": {"lat": 16.9912, "lon": 82.2344, "tz": "Asia/Kolkata"},
        "East Godavari (Rajahmundry)": {"lat": 17.0006, "lon": 81.7925, "tz": "Asia/Kolkata"},
        "Konaseema": {"lat": 16.7115, "lon": 82.0294, "tz": "Asia/Kolkata"},
        "West Godavari (Bhimavaram)": {"lat": 16.5332, "lon": 81.5230, "tz": "Asia/Kolkata"},
        "Eluru": {"lat": 16.7115, "lon": 81.1070, "tz": "Asia/Kolkata"},
        "Krishna (Machilipatnam)": {"lat": 16.1833, "lon": 81.1333, "tz": "Asia/Kolkata"},
        "NTR (Vijayawada)": {"lat": 16.5062, "lon": 80.6480, "tz": "Asia/Kolkata"},
        "Guntur": {"lat": 16.3056, "lon": 80.4402, "tz": "Asia/Kolkata"},
        "Palnadu": {"lat": 16.2575, "lon": 79.9922, "tz": "Asia/Kolkata"},
        "Bapatla": {"lat": 15.8972, "lon": 80.4659, "tz": "Asia/Kolkata"},
        "Prakasam (Ongole)": {"lat": 15.5000, "lon": 80.0500, "tz": "Asia/Kolkata"},
        "Nellore": {"lat": 14.4426, "lon": 79.9865, "tz": "Asia/Kolkata"},
        
        # Rayalaseema
        "Kurnool": {"lat": 15.8224, "lon": 78.0385, "tz": "Asia/Kolkata"},
        "Nandyal": {"lat": 15.4833, "lon": 78.4833, "tz": "Asia/Kolkata"},
        "Anantapur": {"lat": 14.6819, "lon": 77.6001, "tz": "Asia/Kolkata"},
        "Sri Sathya Sai (Puttaparthi)": {"lat": 14.1678, "lon": 77.8188, "tz": "Asia/Kolkata"},
        "YSR (Kadapa)": {"lat": 14.4682, "lon": 78.8220, "tz": "Asia/Kolkata"},
        "Annamayya (Rayachoti)": {"lat": 14.0500, "lon": 78.7500, "tz": "Asia/Kolkata"},
        "Tirupati": {"lat": 13.6288, "lon": 79.4192, "tz": "Asia/Kolkata"},
        "Chittoor": {"lat": 13.1876, "lon": 79.1026, "tz": "Asia/Kolkata"},
    },
    
    # Keep your other states below this line:
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

def rashi_from_sidereal_sun(sun_sid: float):
    """Return Rashi (Sun Sign) name, index 1..12, degrees into rashi"""
    idx = int((sun_sid % 360) // 30)
    deg_into = (sun_sid % 360) - idx * 30
    names = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
             "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return names[idx], idx + 1, deg_into

def masa_from_sidereal(sun_sid: float):
    """Approximate lunar month name from sidereal sun (Amanta-style approx)."""
    idx = int(((sun_sid + 30) % 360) // 30)
    months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
              "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
              "Magha", "Phalguna"]
    return months[idx]

# --- Helper to get local time for default ---
def get_local_time(tz_name):
    try:
        tz = pytz.timezone(tz_name)
        return datetime.now(tz).time().replace(second=0, microsecond=0)
    except Exception:
        return dtime(6, 0)

# -----------------------
# Streamlit UI (modern look)
# -----------------------
st.set_page_config(page_title="Vedic DOB — Modern UI", layout="centered")
st.markdown("<h1 style='text-align:center'>📿 Vedic DOB — Accurate & Fast</h1>", unsafe_allow_html=True)
st.write("Enter birth details. Results use topocentric sidereal positions (Lahiri) for high accuracy.")

# Initialize session state for persistent data
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
    
if 'state' not in st.session_state:
    st.session_state.state = sorted(DISTRICT_DATA.keys())[0]
if 'district' not in st.session_state:
    st.session_state.district = sorted(DISTRICT_DATA[st.session_state.state].keys())[0]

# left column: inputs; right column: results
col1, col2 = st.columns([1, 1])

# --- INPUT SECTION ---
with col1:
    name = st.text_input("Full name", key='input_name')
    dob = st.date_input("Date of birth", min_value=date(1900, 1, 1), max_value=date.today(), key='input_dob')
    
    # Get current timezone info for the birth time suggestion
    current_tz_name = DISTRICT_DATA.get(st.session_state.state, {}).get(st.session_state.district, {}).get("tz", "Asia/Kolkata")
    birth_time = st.time_input("Time of birth (local)", value=get_local_time(current_tz_name), key='input_time')
    
    st.markdown("**Place of birth**")
    
    # Place selection: Changes will cause a rerun, naturally updating the district list
    state = st.selectbox("State", sorted(DISTRICT_DATA.keys()), key='selected_state')
    
    # Ensure district selection list is based on the current state
    district_list = sorted(DISTRICT_DATA.get(state, {}).keys())
    if st.session_state.district not in district_list or not district_list:
        st.session_state.district = district_list[0] if district_list else ""
        
    district = st.selectbox("District", district_list, key='selected_district')
    
    manual = st.checkbox("Manual lat/lon override", value=False, key='input_manual')
    
    # Initialize lat/lon/tz based on selected district
    default_data = DISTRICT_DATA.get(state, {}).get(district, {"lat": 0.0, "lon": 0.0, "tz": "UTC"})
    default_lat = default_data["lat"]
    default_lon = default_data["lon"]
    tz_name = default_data["tz"]

    if manual:
        lat = st.number_input("Latitude (deg, north +)", value=float(default_lat), key='input_lat')
        lon = st.number_input("Longitude (deg, east +)", value=float(default_lon), key='input_lon')
        tz_name = st.text_input("Timezone (IANA)", value=tz_name, key='input_tz')
    else:
        lat = default_lat
        lon = default_lon
        # tz_name is already set to default_data["tz"]

    st.markdown("---")
    # --- INPUT FOR YEAR SEARCH ---
    current_year = date.today().year
    year_to_search = st.number_input(
        "Find Vedic DOB starting from year:",
        min_value=dob.year + 1,
        max_value=current_year + 5,
        value=current_year,
        step=1,
        key='input_year_search'
    )
    # -----------------------------
    
    # The submit button now triggers the main calculation logic
    submit = st.button("Calculate Vedic DOB & Anniversaries", key='submit_button')
# --- END INPUT SECTION ---

with col2:
    st.empty()  # placeholder for results

# handle submit (or rerun after input change)
if submit or st.session_state.calculated:
    
    # Set calculated flag to maintain results on rerun
    st.session_state.calculated = True
    
    # --- Retrieve values from session state ---
    name = st.session_state.input_name
    dob = st.session_state.input_dob
    birth_time = st.session_state.input_time
    state = st.session_state.selected_state
    district = st.session_state.selected_district
    
    if st.session_state.input_manual:
        lat = st.session_state.input_lat
        lon = st.session_state.input_lon
        tz_name = st.session_state.input_tz
    else:
        # Recalculate defaults if not manual
        default_data = DISTRICT_DATA.get(state, {}).get(district, {"lat": 0.0, "lon": 0.0, "tz": "UTC"})
        lat = default_data["lat"]
        lon = default_data["lon"]
        tz_name = default_data["tz"]

    year_to_search = st.session_state.input_year_search
    # ----------------------------------------
    
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
    rashi_name, rashi_idx, rashi_deg = rashi_from_sidereal(moon_sid)
    sun_rashi_name, sun_rashi_idx, sun_rashi_deg = rashi_from_sidereal_sun(sun_sid)
    masa_name = masa_from_sidereal(sun_sid)
    weekday = local_dt.strftime("%A")

    # Display results in col2
    with col2:
        st.markdown("---")
        st.markdown(f"## ✨ Results for **{name or '—'}**")
        st.markdown(f"**Birth (local):** {local_dt.strftime('%Y-%m-%d %H:%M:%S')} — `{state} / {district}`")
        st.markdown("---")

        # cards: three columns (Using st.markdown for full name display)
        c1, c2, c3 = st.columns(3)
        
        # Change 1: Use st.markdown/st.write to avoid metric truncation
        with c1:
            st.markdown(f"**Tithi**")
            st.write(f"**{tname}** (#{tnum})")
            st.caption(f"{paksha}")
            
        with c2:
            st.markdown(f"**Rashi (Moon sign)**")
            st.write(f"**{rashi_name}**")
            st.caption(f"{rashi_deg:.2f}° into sign")
            
        with c3:
            st.markdown(f"**Nakshatra**")
            st.write(f"**{nak_name}**")
            st.caption(f"Pada {nak_pada}")

        # second row: masa, weekday, sun sign
        c4, c5, c6 = st.columns(3)
        c4.metric(label="Masa (approx.)", value=masa_name)
        c5.metric(label="Weekday", value=weekday)
        c6.metric(label="Rashi (Sun sign)", value=f"{sun_rashi_name}", delta=f"{sun_rashi_deg:.2f}° into sign")

        # diagnostics & raw numbers
        with st.expander("Diagnostics & Raw numbers (click to open)"):
            st.write(f"Ayanamsa (Lahiri) used: **{ay_deg:.6f}°**")
            st.write(f"Sun (sidereal) : {sun_sid:.6f}°")
            st.write(f"Moon (sidereal): {moon_sid:.6f}°")
            st.write(f"Tithi angle (Moon - Sun): {tangle:.6f}°")
            st.write(f"Nakshatra #{nak_idx} — {nak_deg:.6f}° into nakshatra")
            st.write(f"Moon Rashi idx: {rashi_idx} (1..12), {rashi_deg:.6f}° into rashi")
            st.write(f"Sun Rashi idx: {sun_rashi_idx} (1..12), {sun_rashi_deg:.6f}° into rashi")
            st.write("Coordinates used:", f"{lat:.6f}°N, {lon:.6f}°E")
            st.write("Local timezone:", tz_name)

        # --- Anniversary Search Logic ---

        def find_vedic_anniversary(start_date_obj: date, max_days=380):
            # Determine the local timezone for search iteration
            try:
                local_tz = pytz.timezone(tz_name)
            except Exception:
                local_tz = pytz.timezone("Asia/Kolkata")

            # Set search time to noon local time for consistent comparison
            start_dt_localized = local_tz.localize(datetime.combine(start_date_obj, dtime(12, 0)))

            for i in range(max_days):
                cand_local = start_dt_localized + timedelta(days=i)
                cand_utc = cand_local.astimezone(pytz.utc)
                jd_c = jd_from_utc(cand_utc)

                # Stop search after a reasonable cycle (365 days)
                if i >= 365 and cand_local.date() > start_date_obj + timedelta(days=365):
                     break

                try:
                    s_c, m_c, _ = sun_moon_sidereal_topo(jd_c, lon, lat, 0.0)
                except Exception:
                    continue

                tnum_c, _, _, _ = tithi_from_sidereal(s_c, m_c)
                nak_c, _, _, _ = nakshatra_from_sidereal(m_c)
                rashi_c, _, _ = rashi_from_sidereal(m_c)
                masa_c = masa_from_sidereal(s_c)

                # Full Match (Tithi, Nakshatra, Moon Rashi, Masa)
                if (tnum_c == tnum and nak_c == nak_name and rashi_c == rashi_name and masa_c == masa_name):
                    return cand_local.date()

            return None
        
        # Determine the correct start date for the requested year
        if year_to_search == current_year:
            # If current year, search starts from today to find UPCOMING DOB
            start_date_requested_year = date.today()
        else:
            # If future year, search starts from Jan 1st
            start_date_requested_year = date(year_to_search, 1, 1)

        with st.spinner(f"Searching for Vedic DOB in **{year_to_search}**..."):
            vedic_dob_requested_year = find_vedic_anniversary(start_date_requested_year)

        # 2. Search for the next year
        if vedic_dob_requested_year:
            # Start search one day after the first found date
            start_date_next_year = vedic_dob_requested_year + timedelta(days=1)
        else:
            # If the requested year's DOB wasn't found, start the next search from Jan 1st of the next year.
            start_date_next_year = date(year_to_search + 1, 1, 1)

        with st.spinner(f"Searching for Vedic DOB in **{year_to_search + 1}**..."):
            vedic_dob_next_year = find_vedic_anniversary(start_date_next_year)
            
        # --- End Anniversary Search Logic ---

        # Update UI to show the selected year and next year dates
        st.markdown("---")

        # Removed Solar birthday section completely
        
        # Vedic Anniversaries
        st.markdown("### 🌙 Exact Vedic DOB (Tithi + Nakshatra + Rashi + Masa)")
        c9, c10 = st.columns(2)

        # --- MODIFIED: Ensure full name display and better handling of 'Not Found' ---
        if vedic_dob_requested_year:
            requested_year_weekday = vedic_dob_requested_year.strftime('%A')
            requested_year_value = str(vedic_dob_requested_year)
        else:
            requested_year_weekday = "N/A"
            if year_to_search == current_year:
                 requested_year_value = f"Passed already in {year_to_search}"
            else:
                 requested_year_value = f"Not found in {year_to_search}"


        if vedic_dob_next_year:
            next_year_weekday = vedic_dob_next_year.strftime('%A')
            next_year_value = str(vedic_dob_next_year)
        else:
            next_year_weekday = "N/A"
            next_year_value = f"Not found in {year_to_search + 1}"
            
        # Display Anniversary Results using markdown for full date/day display
        with c9:
            st.markdown(f"**Anniversary in {year_to_search}**")
            st.markdown(f"<p style='font-size:1.5rem; font-weight:bold'>{requested_year_value}</p>", unsafe_allow_html=True)
            if requested_year_weekday != "N/A":
                st.markdown(f"<p style='color:green; font-weight:600'>{requested_year_weekday}</p>", unsafe_allow_html=True)

        with c10:
            st.markdown(f"**Anniversary in {year_to_search + 1}**")
            st.markdown(f"<p style='font-size:1.5rem; font-weight:bold'>{next_year_value}</p>", unsafe_allow_html=True)
            if next_year_weekday != "N/A":
                st.markdown(f"<p style='color:green; font-weight:600'>{next_year_weekday}</p>", unsafe_allow_html=True)


        # Save to Supabase (optional)
        if supabase:
            try:
                # Solar birthday is removed from the data saved
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
                    "vedic_sun_rashi": sun_rashi_name,
                    "requested_year_vedic_dob": requested_year_value,
                    "next_year_vedic_dob": next_year_value
                }).execute()
                st.success("Saved to Supabase ✅")
            except Exception as e:
                st.error(f"Could not save to Supabase: {e}")

st.markdown("---")
st.caption("Modern UI · Topocentric sidereal calculations (Lahiri) · Expand diagnostics for raw numbers. Add more districts in DISTRICT_DATA for coverage.")
