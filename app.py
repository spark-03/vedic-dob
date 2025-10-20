import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import ephem
import panchanga

st.title("📿 Vedic Date of Birth Finder")

# --- Supabase Setup ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("❌ Supabase credentials missing in Streamlit Secrets!")

# --- Create a class for place ---
class Place:
    def __init__(self, latitude, longitude, timezone):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone

# --- Default place (you can change or make it user-selectable) ---
place = Place(latitude=17.3850, longitude=78.4867, timezone=5.5)  # Hyderabad, India

# --- Convert to Julian Day ---
def to_julian_day(date_obj):
    obs = ephem.Observer()
    obs.date = date_obj.strftime("%Y/%m/%d")
    return ephem.julian_date(obs.date)

# --- Next Year Vedic DOB Calculation ---
def next_year_same_tithi(dob):
    jd_birth = to_julian_day(dob)
    tithi_birth = panchanga.tithi(jd_birth, place)
    masa_birth = panchanga.masa(jd_birth, place)

    try:
        check_date = datetime(dob.year + 1, dob.month, dob.day)
    except ValueError:
        check_date = datetime(dob.year + 1, 1, 1)

    end_date = datetime(dob.year + 1, 12, 31)
    while check_date <= end_date:
        jd_check = to_julian_day(check_date)
        if (
            panchanga.tithi(jd_check, place) == tithi_birth
            and panchanga.masa(jd_check, place) == masa_birth
        ):
            return check_date.date()
        check_date += timedelta(days=1)
    return end_date.date()

# --- User Inputs ---
name = st.text_input("Enter your Name")
dob = st.date_input(
    "Enter your Date of Birth",
    min_value=date(1900, 1, 1),
    max_value=date.today()
)

# --- On Submit ---
if st.button("Submit"):
    if not name:
        st.warning("Please enter your name!")
    else:
        jd = to_julian_day(dob)
        vedic_tithi = panchanga.tithi(jd, place)
        vedic_nakshatra = panchanga.nakshatra(jd, place)
        vedic_masa = panchanga.masa(jd, place)
        weekday = dob.strftime("%A")

        next_year_dob = next_year_same_tithi(dob)

        st.success(
            f"Hello {name}!\n\n"
            f"📿 **Vedic DOB Details:**\n"
            f"- Tithi: {vedic_tithi}\n"
            f"- Nakshatra: {vedic_nakshatra}\n"
            f"- Masa: {vedic_masa}\n"
            f"- Weekday: {weekday}\n\n"
            f"📅 **Next year's same Vedic DOB (Gregorian):** {next_year_dob}"
        )

        # --- Save to Supabase ---
        try:
            supabase.table("users").insert({
                "name": name,
                "dob": dob.isoformat(),
                "vedic_details": f"{vedic_tithi}, {vedic_nakshatra}, {vedic_masa}, {weekday}"
            }).execute()
            st.info("✅ Data saved successfully to Supabase!")
        except Exception as e:
            st.error(f"⚠️ Could not save to database: {e}")