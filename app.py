import streamlit as st
from supabase import create_client
from datetime import datetime, date, timedelta
import swisseph as swe
import math

st.set_page_config(page_title="📿 Vedic DOB Finder", page_icon="📿", layout="centered")
st.title("📿 Vedic DOB — Accurate & Fast")

# --- Supabase Setup ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("❌ Supabase URL or Key not found in Streamlit Secrets!")

# --- Input ---
name = st.text_input("Full Name")
dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
t_birth = st.time_input("Time of Birth (Local)", value=datetime.now().time())

state_options = ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu"]
state = st.selectbox("State", state_options)

district_coords = {
    "Nellore": (14.4426, 79.9865),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Bangalore": (12.9716, 77.5946)
}
district = st.selectbox("District", list(district_coords.keys()))
lat, lon = district_coords[district]
timezone_offset = 5.5  # IST

# --- Panchanga Functions ---
def datetime_to_jd(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60 + dt.second/3600)

def sun_moon_sidereal_topo(jd_ut, lon, lat):
    # Get tropical positions
    sun = swe.calc_ut(jd_ut, swe.SUN)[0]
    moon = swe.calc_ut(jd_ut, swe.MOON)[0]
    # Ayanamsa for Lahiri
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)
    sun_sid = (sun - ayanamsa) % 360
    moon_sid = (moon - ayanamsa) % 360
    return sun_sid, moon_sid

def get_tithi(sun_lon, moon_lon):
    diff = (moon_lon - sun_lon) % 360
    return int(diff / 12) + 1  # 1..30

def tithi_name(tithi):
    names = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
             "Sashti", "Saptami", "Ashtami", "Navami", "Dashami",
             "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"]
    if tithi <= 15:
        return f"Shukla {names[tithi-1]}"
    else:
        return f"Krishna {names[tithi-16]}"

def get_nakshatra(moon_lon):
    index = int(moon_lon / (360/27))
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                  "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                  "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                  "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return nakshatras[index]

def get_rashi(moon_lon):
    rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
              "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return rashis[int(moon_lon / 30) % 12]

def get_masa(sun_lon):
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    return lunar_months[int((sun_lon+30)/30)%12]

def find_next_exact_vedic(local_dt_localized: datetime, max_days: int = 450):
    jd_birth = datetime_to_jd(local_dt_localized)
    sun_sid_birth, moon_sid_birth = sun_moon_sidereal_topo(jd_birth, lon, lat)
    tithi_birth = get_tithi(sun_sid_birth, moon_sid_birth)
    nakshatra_birth = get_nakshatra(moon_sid_birth)
    rashi_birth = get_rashi(moon_sid_birth)
    masa_birth = get_masa(sun_sid_birth)

    start_date = local_dt_localized + timedelta(days=1)
    for i in range(max_days):
        d = start_date + timedelta(days=i)
        jd = datetime_to_jd(d)
        sun_sid, moon_sid = sun_moon_sidereal_topo(jd, lon, lat)
        if (get_tithi(sun_sid, moon_sid) == tithi_birth and
            get_nakshatra(moon_sid) == nakshatra_birth and
            get_rashi(moon_sid) == rashi_birth and
            get_masa(sun_sid) == masa_birth):
            return d.date()
    return start_date.date()

# --- Button Action ---
if st.button("Calculate Vedic DOB"):
    if not name:
        st.warning("Please enter your name!")
    else:
        dt_birth = datetime.combine(dob, t_birth)
        jd = datetime_to_jd(dt_birth)
        sun_lon, moon_lon = sun_moon_sidereal_topo(jd, lon, lat)
        tithi_num = get_tithi(sun_lon, moon_lon)
        vedic_tithi = tithi_name(tithi_num)
        nakshatra = get_nakshatra(moon_lon)
        rashi = get_rashi(moon_lon)
        masa = get_masa(sun_lon)
        weekday = dt_birth.strftime("%A")
        next_vedic_dob = find_next_exact_vedic(dt_birth)

        st.success(f"✨ Results for **{name}**")
        st.write(f"**Birth (local):** {dt_birth} — {state} / {district}")
        st.write(f"- Tithi: {vedic_tithi} ({tithi_num})")
        st.write(f"- Nakshatra: {nakshatra}")
        st.write(f"- Rashi (Moon sign): {rashi}")
        st.write(f"- Masa (approx.): {masa}")
        st.write(f"- Weekday: {weekday}")
        st.write(f"- Solar birthday (next year): {date(dt_birth.year+1, dt_birth.month, dt_birth.day)}")
        st.write(f"📅 Next exact Vedic birthday (matching Tithi+Masa+Nakshatra+Rashi): {next_vedic_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("users").insert({
                    "name": name,
                    "dob": dt_birth.isoformat(),
                    "state": state,
                    "district": district,
                    "vedic_details": f"{vedic_tithi}, {nakshatra}, {masa}, {rashi}, {weekday}"
                }).execute()
                st.info("✅ Data saved in Supabase successfully!")
            except Exception as e:
                st.error(f"⚠️ Could not save to Supabase: {e}")

st.caption("Developed by Spark ✨ | Powered by Accurate Panchang Science")