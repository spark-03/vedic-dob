import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import ephem  # pip install ephem

st.title("📿 Vedic Date of Birth Finder (Full Panchang)")

# --- Supabase Setup using Streamlit Secrets ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("❌ Supabase URL or Key not found in Streamlit Secrets!")

# --- Streamlit Input ---
name = st.text_input("Enter your Name")
dob = st.date_input(
    "Enter your Date of Birth",
    min_value=date(1900, 1, 1),
    max_value=date.today()
)

# --- Panchang Calculation Functions ---
def get_tithi(date_obj):
    """Calculate Tithi (Moon-Sun angle)"""
    date_str = date_obj.strftime("%Y/%m/%d")
    moon = ephem.Moon(date_str)
    sun = ephem.Sun(date_str)
    moon_phase_angle = (moon.elong * 180 / 3.14159265) % 360  # degrees
    tithi_num = int(moon_phase_angle / 12) + 1  # 1-30
    return tithi_num

def tithi_name(tithi_num):
    """Map Tithi number to name and Paksha"""
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", 
              "Sashti", "Saptami", "Ashtami", "Navami", "Dashami", 
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", 
              "Purnima", "Amavasya"]
    if tithi_num <= 15:
        paksha = "Shukla"
        tithi = tithis[tithi_num - 1]
    else:
        paksha = "Krishna"
        tithi = tithis[(tithi_num - 16) % 15]
    return f"{paksha} {tithi}"

def get_nakshatra(date_obj):
    """Calculate Nakshatra"""
    date_str = date_obj.strftime("%Y/%m/%d")
    moon = ephem.Moon(date_str)
    nakshatra_num = int((moon.ra * 180 / 3.14159265) / (360/27))  # 27 Nakshatras
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                  "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                  "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                  "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return nakshatras[nakshatra_num % 27]

def get_masa(date_obj):
    """Estimate lunar month based on Sun’s longitude"""
    date_str = date_obj.strftime("%Y/%m/%d")
    sun = ephem.Sun(date_str)
    sun_longitude = sun.ra * 180 / 3.14159265  # in degrees
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    month_index = int(sun_longitude / 30) % 12
    return lunar_months[month_index]

def next_year_same_tithi(dob):
    """Find next Gregorian date with same Tithi next year"""
    tithi_birth = get_tithi(dob)
    next_year = dob.year + 1
    check_date = datetime(next_year, 1, 1)
    while True:
        if get_tithi(check_date) == tithi_birth:
            return check_date.date()
        check_date += timedelta(days=1)

# --- Submit Button ---
if st.button("Submit"):
    if not name:
        st.warning("Please enter your name!")
    else:
        tithi_num = get_tithi(dob)
        vedic_tithi = tithi_name(tithi_num)
        nakshatra = get_nakshatra(dob)
        masa = get_masa(dob)
        weekday = dob.strftime("%A")
        next_year_dob = next_year_same_tithi(dob)

        st.success(f"Hello {name}!\n\n"
                   f"📿 Your Vedic DOB:\n"
                   f"- Tithi: {vedic_tithi}\n"
                   f"- Nakshatra: {nakshatra}\n"
                   f"- Masa: {masa}\n"
                   f"- Weekday: {weekday}\n\n"
                   f"📅 Next year's Gregorian date with same Tithi: {next_year_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("vedic_dobs").insert({
                    "name": name,
                    "dob": dob.isoformat(),
                    "vedic_details": f"{vedic_tithi}, {nakshatra}, {masa}, {weekday}"
                }).execute()
                st.info("✅ Your data has been saved in the database!")
            except Exception as e:
                st.error(f"⚠️ Could not save to database: {e}")