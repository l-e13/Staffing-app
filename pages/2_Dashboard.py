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

# Rename columns
df = df.rename(columns={
    "roster_date": "Date",
    "name": "Name",
    "division": "Division",
    "code": "Code",
    "hours": "Hours",
    "position": "Position"
})

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", [])
    member = st.selectbox("Select member", ["All"] + sorted(df["Name"].dropna().unique()))
    code_filter = st.multiselect("Shift Code", sorted(df["Code"].dropna().unique()))
    division_filter = st.multiselect("Division", sorted(df["Division"].dropna().unique()))

# Apply filters
if date_range and len(date_range) == 2:
    df = df[(df["Date"] >= str(date_range[0])) & (df["Date"] <= str(date_range[1]))]
if member != "All":
    df = df[df["Name"] == member]
if code_filter:
    df = df[df["Code"].isin(code_filter)]
if division_filter:
    df = df[df["Division"].isin(division_filter)]

# Metrics
st.subheader("📌 Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Entries", len(df))
col2.metric("Total Hours", round(df["Hours"].sum(), 2))
col3.metric("Unique Members", df["Name"].nunique())

# Charts
st.subheader("📈 Hours by Division")
if "Division" in df.columns and "Hours" in df.columns:
    st.bar_chart(df.groupby("Division")["Hours"].sum().sort_values(ascending=False))

# Table
st.subheader("📅 Recent Roster Entries")
st.dataframe(df.sort_values("Date", ascending=False).head(20))

