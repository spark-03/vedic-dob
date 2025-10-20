from datetime import date
import streamlit as st
from supabase import create_client
import panchanga

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Vedic DOB Finder", page_icon="🪔", layout="centered")
st.title("🪔 Vedic Date of Birth Finder")
st.write("Discover your Vedic (lunar) birth details using ancient Panchanga calculations.")

# --- Supabase Setup ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Date Input ---
dob = st.date_input(
    "Select your Date of Birth",
    min_value=date(1900, 1, 1),
    max_value=date.today(),
    help="Choose your date of birth to calculate the corresponding Vedic (lunar) date."
)

# --- Button Action ---
if st.button("🔍 Find My Vedic DOB"):
    try:
        # Calculate Tithi (Vedic lunar day)
        vedic_tithi = panchanga.tithi(dob)

        # Display result
        st.success(f"🪔 Your Vedic Tithi: **{vedic_tithi}**")

        # --- Save to Supabase ---
        try:
            data = {
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