# pages/2_Dashboard.py
import streamlit as st
import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Staffing & WDO Dashboard")

# Load secrets or .env
if "SUPABASE_URL" not in os.environ:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=env_path)

url = os.getenv("SUPABASE_URL") or st.secrets["supabase"]["url"]
key = os.getenv("SUPABASE_KEY") or st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# Load data
res = supabase.table("roster_data").select("*").limit(5000).execute()
df = pd.DataFrame(res.data)

if df.empty:
    st.warning("No data found.")
    st.stop()


