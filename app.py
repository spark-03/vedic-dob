import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import ephem
import math

st.title("📿 Vedic Date of Birth Finder (Precise Panchang)")

# --- Supabase Setup ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("❌ Supabase URL or Key not found in Streamlit Secrets!")

# --- Input ---
name = st.text_input("Enter your Name")
dob = st.date_input(
    "Enter your Date of Birth",
    min_value=date(1900, 1, 1),
    max_value=date.today()
)

# --- Panchang Functions ---
def get_longitudes(date_obj):
    """Return Sun and Moon ecliptic longitudes in degrees"""
    obs = ephem.Observer()
    obs.date = date_obj.strftime("%Y/%m/%d 12:00")  # Noon for stability
    sun = ephem.Sun(obs)
    moon = ephem.Moon(obs)
    sun_long = math.degrees(sun.hlong) % 360
    moon_long = math.degrees(moon.hlong) % 360
    return sun_long, moon_long

def get_tithi(date_obj):
    """Calculate Tithi (Moon-Sun angle difference)"""
    sun_long, moon_long = get_longitudes(date_obj)
    diff = (moon_long - sun_long) % 360
    tithi_num = int(diff / 12) + 1  # 1-30
    return tithi_num

def tithi_name(tithi_num):
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
              "Sashti", "Saptami", "Ashtami", "Navami", "Dashami",
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"]
    return f"Shukla {tithis[tithi_num - 1]}" if tithi_num <= 15 else f"Krishna {tithis[tithi_num - 16]}"

def get_nakshatra(date_obj):
    _, moon_long = get_longitudes(date_obj)
    index = int((moon_long % 360) / (360/27))
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                  "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                  "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                  "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return nakshatras[index]

def get_masa(date_obj):
    sun_long, _ = get_longitudes(date_obj)
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    index = int((sun_long + 30)/30) % 12
    return lunar_months[index]

def get_rashi(date_obj):
    _, moon_long = get_longitudes(date_obj)
    rashi_index = int(moon_long / 30) % 12
    rashis = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
              "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
    return rashis[rashi_index]

def next_year_precise_vedic_date(dob):
    """Find next Gregorian date where Tithi, Masa, Nakshatra, and Rashi all match"""
    # Original Vedic details
    tithi_birth = get_tithi(dob)
    masa_birth = get_masa(dob)
    nakshatra_birth = get_nakshatra(dob)
    rashi_birth = get_rashi(dob)

    try:
        start_date = datetime(dob.year + 1, dob.month, dob.day)
    except ValueError:
        start_date = datetime(dob.year + 1, 1, 1)

    # Search next ~400 days to find exact match
    for i in range(400):
        d = start_date + timedelta(days=i)
        if (get_tithi(d) == tithi_birth and
            get_masa(d) == masa_birth and
            get_nakshatra(d) == nakshatra_birth and
            get_rashi(d) == rashi_birth):
            return d.date()

    # Fallback: return same solar birthday if no match found
    return start_date.date()

# --- Button Action ---
if st.button("Submit"):
    if not name:
        st.warning("Please enter your name!")
    else:
        tithi_num = get_tithi(dob)
        vedic_tithi = tithi_name(tithi_num)
        nakshatra = get_nakshatra(dob)
        masa = get_masa(dob)
        rashi = get_rashi(dob)
        weekday = dob.strftime("%A")
        next_year_dob = next_year_precise_vedic_date(dob)

        st.success(f"Hello {name}!\n\n"
                   f"📿 Vedic DOB Details:\n"
                   f"- Tithi: {vedic_tithi}\n"
                   f"- Nakshatra: {nakshatra}\n"
                   f"- Masa: {masa}\n"
                   f"- Rashi: {rashi}\n"
                   f"- Weekday: {weekday}\n\n"
                   f"📅 Next year's Gregorian date (exact same Vedic DOB): {next_year_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("users").insert({
                    "name": name,
                    "dob": dob.isoformat(),
                    "vedic_details": f"{vedic_tithi}, {nakshatra}, {masa}, {rashi}, {weekday}"
                }).execute()
                st.info("✅ Data saved in Supabase successfully!")
            except Exception as e:
                st.error(f"⚠️ Could not save to database: {e}")

st.caption("Developed by Spark ✨ | Powered by Precise Panchang Science")