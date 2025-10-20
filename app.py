import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import ephem
import math

st.title("📿 Vedic Date of Birth Finder (Accurate Panchang Calculation)")

# --- Supabase Setup using Streamlit Secrets ---
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

# --- Core Panchang Logic ---
def get_longitudes(date_obj):
    """Return (sun_long, moon_long) in degrees for given date"""
    obs = ephem.Observer()
    obs.date = date_obj.strftime("%Y/%m/%d 12:00")  # Noon for stability
    sun = ephem.Sun(obs)
    moon = ephem.Moon(obs)
    sun_long = math.degrees(sun.hlong) % 360
    moon_long = math.degrees(moon.hlong) % 360
    return sun_long, moon_long

def get_tithi(date_obj):
    """Calculate lunar tithi accurately based on Sun–Moon ecliptic difference"""
    sun_long, moon_long = get_longitudes(date_obj)
    diff = (moon_long - sun_long) % 360
    tithi_num = int(diff / 12) + 1  # 30 tithis in a lunar month
    return tithi_num

def tithi_name(tithi_num):
    """Return name and Paksha"""
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
              "Sashti", "Saptami", "Ashtami", "Navami", "Dashami",
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"]
    if tithi_num <= 15:
        return f"Shukla {tithis[tithi_num - 1]}"
    else:
        return f"Krishna {tithis[tithi_num - 16]}"

def get_nakshatra(date_obj):
    """Calculate nakshatra from Moon longitude"""
    sun_long, moon_long = get_longitudes(date_obj)
    nakshatra_index = int((moon_long % 360) / (360 / 27))
    nakshatras = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
                  "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
                  "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
                  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
                  "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
                  "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    return nakshatras[nakshatra_index]

def get_masa(date_obj):
    """Estimate lunar month using Sun’s longitude at new moon boundaries"""
    sun_long, moon_long = get_longitudes(date_obj)
    month_index = int((sun_long + 30) / 30) % 12
    lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana",
                    "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha",
                    "Magha", "Phalguna"]
    return lunar_months[month_index]

def next_year_same_tithi(dob):
    """Find next Gregorian date with same Tithi and Masa next year"""
    tithi_birth = get_tithi(dob)
    masa_birth = get_masa(dob)
    try:
        check_date = datetime(dob.year + 1, dob.month, dob.day)
    except ValueError:
        check_date = datetime(dob.year + 1, 1, 1)
    end_date = datetime(dob.year + 1, 12, 31)

    while check_date <= end_date:
        if get_tithi(check_date) == tithi_birth and get_masa(check_date) == masa_birth:
            return check_date.date()
        check_date += timedelta(days=1)
    return end_date.date()

# --- Button Action ---
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
                   f"📅 Next year's date (same Tithi & Masa): {next_year_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("users").insert({
                    "name": name,
                    "dob": dob.isoformat(),
                    "vedic_details": f"{vedic_tithi}, {nakshatra}, {masa}, {weekday}"
                }).execute()
                st.info("✅ Data saved in Supabase successfully!")
            except Exception as e:
                st.error(f"⚠️ Could not save to database: {e}")

st.caption("Developed by Spark ✨ | Powered by Ancient Panchang Science")
