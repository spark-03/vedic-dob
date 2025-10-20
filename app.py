import streamlit as st
from supabase import create_client
import os
from datetime import date, datetime

st.title("📅 Vedic Date of Birth Finder")

# --- Supabase Setup ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Missing Supabase credentials! Add SUPABASE_URL and SUPABASE_KEY in GitHub → Settings → Secrets → Actions.")
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Streamlit Input ---
name = st.text_input("Enter your Name")

dob = st.date_input(
    "Enter your Date of Birth",
    min_value=date(1900, 1, 1),  # allow DOBs from 1900
    max_value=date.today()        # cannot be future
)

# --- Placeholder Vedic DOB calculation ---
def get_placeholder_vedic_dob(dob):
    # Simple simulated Tithi (you can replace with real calculation later)
    tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", 
              "Sashti", "Saptami", "Ashtami", "Navami", "Dashami", 
              "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", 
              "Purnima", "Amavasya"]
    index = dob.day % 15
    paksha = "Shukla" if dob.day <= 15 else "Krishna"
    return f"{paksha} {tithis[index]}"

if st.button("Submit"):
    if not name:
        st.warning("Please enter your name!")
    else:
        vedic_result = get_placeholder_vedic_dob(dob)
        next_year_dob = dob.replace(year=dob.year + 1)  # temporary next-year date

        st.success(f"Hello {name}!\nYour Vedic DOB: {vedic_result}\nNext year's date: {next_year_dob}")

        # --- Save to Supabase ---
        if 'supabase' in locals():
            try:
                supabase.table("vedic_dobs").insert({
                    "name": name,
                    "dob": dob.isoformat(),
                    "vedic_details": vedic_result
                }).execute()
                st.info("✅ Your data has been saved in the database!")
            except Exception as e:
                st.error(f"⚠️ Could not save to database: {e}")