# Home.py
import streamlit as st

st.set_page_config(page_title="Welcome", layout="centered")

st.title("👋 Welcome to the Fire Staffing App")

st.markdown("""
This app helps track and analyze fire & EMS staffing through daily roster uploads.

### 🔍 Features:
- **Roster Ingestion**: Upload Excel files to populate the live Supabase database.
- **WDO Dashboard**: Analyze working day off data, shift codes, and hours worked.

Use the sidebar to navigate between pages 👉
""")

