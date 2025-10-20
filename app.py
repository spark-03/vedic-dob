import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import requests

# --- Supabase Setup ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

st.title("📿 Vedic Date of Birth Finder")

name = st.text_input("Enter your Name")
dob = st.date_input(
    "Enter your Date of Birth",
    min_value=date(1900, 1, 1),  # allow as early as 1900
    max_value=date.today()        # cannot select future dates
)
def get_tithi(date):
    """Call Drik Panchang-like API for Tithi (simple free endpoint)."""
    try:
        api_url = f"https://api.api-ninjas.com/v1/holidays?country=IN&year={date.year}"
        # This is dummy request, you can replace with Drik Panchang or your own logic
        # For demo, we'll return pseudo Tithi
        tithis = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Sashti",
                  "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
                  "Trayodashi", "Chaturdashi", "Purnima", "Amavasya"]
        index = date.day % 15
        paksha = "Shukla" if date.day <= 15 else "Krishna"
        return f"{paksha} {tithis[index]} (Simulated)"
    except:
        return "Error getting Tithi"

if st.button("Submit"):
    vedic_dob = get_tithi(dob)
    # Simulate next year's same Tithi
    next_year_dob = dob.replace(year=dob.year + 1)

    data = {
        "name": name,
        "dob": dob.isoformat(),
        "vedic_dob": vedic_dob,
        "next_year_dob": next_year_dob.isoformat()
    }
    supabase.table("users").insert(data).execute()

    st.success(f"✅ Saved! In {dob.year+1}, your Vedic DOB ({vedic_dob}) will fall on {next_year_dob}")