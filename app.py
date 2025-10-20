import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- Supabase Setup ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# --- Streamlit UI ---
st.title("📅 Vedic DOB Finder")

name = st.text_input("Enter your Name")
dob = st.date_input("Enter your Date of Birth")

if st.button("Submit"):
    # Placeholder Vedic DOB conversion
    vedic_dob = "Tithi XYZ, Masa ABC"
    next_year_dob = dob.replace(year=dob.year + 1)  # temp logic

    # Save to DB
    data = {
        "name": name,
        "dob": dob.isoformat(),
        "vedic_dob": vedic_dob,
        "next_year_dob": next_year_dob.isoformat()
    }
    supabase.table("users").insert(data).execute()

    st.success(f"✅ Saved! In {dob.year+1}, your Vedic DOB will fall on {next_year_dob}")
