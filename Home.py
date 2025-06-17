# Home.py
import streamlit as st

st.set_page_config(page_title="Welcome", layout="centered")

st.title("Welcome to the Staffing App")

st.markdown("""
This app helps track and analyze DC staffing through daily roster uploads.

### Features:
- **Roster Ingestion**: Upload Excel files to populate the live database.
- **Dasboard**: Analyze staffing using the dashboard.

Use the sidebar to navigate between pages
""")

