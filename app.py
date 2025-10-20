import streamlit as st
from datetime import date
from supabase import create_client
import panchanga

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Vedic DOB Finder", page_icon="🪔", layout="centered")
st.title("🪔 Vedic Date of Birth Finder")
st.write("Discover your Vedic (lunar) birth details using ancient Panchanga calculations.")

# --- Supabase Setup ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    st.write("✅ Connected to Supabase successfully!")
except KeyError:
    st.error("⚠️ Supabase keys missing! Please add them in Streamlit secrets.")
    st.stop()

# --- Input Section ---
name = st.text_input("Enter your name")
dob = st.date_input(
    "Select your Date of Birth",
    min_value=date(1900, 1, 1),
    max_value=date.today(),
    help="Choose your date of birth to calculate the corresponding Vedic (lunar) date."
)

# --- Action Button ---
if st.button("🔍 Find My Vedic DOB"):
    if not name:
        st.warning("Please enter your name before continuing.")
    else:
        try:
            # Calculate Vedic Tithi (basic lunar logic)
            vedic_tithi = panchanga.tithi(dob)
            st.success(f"🪔 Your Vedic Tithi is: **{vedic_tithi}**")

            # Save details to Supabase
            try:
                data = {
                    "name": name,
                    "dob": str(dob),
                    "vedic_details": vedic_tithi
                }
                supabase.table("users").insert(data).execute()
                st.info("✅ Your details have been saved successfully in the database.")
            except Exception as e:
                st.error(f"❌ Could not save to Supabase: {e}")

        except Exception as e:
            st.error(f"⚠️ Error calculating Vedic DOB: {e}")

# --- Footer ---
st.markdown("---")
st.caption("Developed by **Spark** ✨ | Powered by ancient Panchanga science")
