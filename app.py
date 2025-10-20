import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import ephem
import panchanga  # Your copied panchanga.py

st.title("📿 Vedic Date of Birth Finder")

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

# --- Next Year Vedic DOB Function ---
def next_year_same_tithi(dob):
    """
    Finds the next Gregorian date with the same Tithi and Masa
    in the next year, roughly in the same season.
    """
    tithi_birth = panchanga.tithi(dob)
    masa_birth = panchanga.masa(dob)

    try:
        check_date = datetime(dob.year + 1, dob.month, dob.day)
    except ValueError:
        check_date = datetime(dob.year + 1, 1, 1)
    end_date = datetime(dob.year + 1, 12, 31)

    while check_date <= end_date:
        if panchanga.tithi(check_date) == tithi_birth and panchanga.masa(check_date) == masa_birth:
            return check_date.date()
        check_date += timedelta(days=1)
    return end_date.date()

# --- Submit Button ---
if st.button("Submit"):
    if not name:
        st.warning("Please enter your name!")
    else:
        # Get Vedic details from panchanga.py
        vedic_tithi = panchanga.tithi(dob)
        nakshatra = panchanga.nakshatra(dob)
        masa = panchanga.masa(dob)
        weekday = dob.strftime("%A")

        # Get next year's Vedic DOB
        next_year_dob = next_year_same_tithi(dob)

        # Display results
        st.success(f"Hello {name}!\n\n"
                   f"📿 Your Vedic DOB:\n"
                   f"- Tithi: {vedic_tithi}\n"
                   f"- Nakshatra: {nakshatra}\n"
                   f"- Masa: {masa}\n"
                   f"- Weekday: {weekday}\n\n"
                   f"📅 Next year's Gregorian date with same Tithi & Masa: {next_year_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("users").insert({
                    "name": name,
                    "dob": dob.isoformat(),
                    "vedic_details": f"{vedic_tithi}, {nakshatra}, {masa}, {weekday}"
                }).execute()
                st.info("✅ Your data has been saved in the database!")
            except Exception as e:
                st.error(f"⚠️ Could not save to database: {e}")