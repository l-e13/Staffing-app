import streamlit as st
import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import os

st.set_page_config(page_title="Roster Ingestion", layout="centered")


pwd = st.sidebar.text_input("Password", type="password")

if not pwd or pwd != st.secrets["app_password"]:
    st.title("Welcome to the Roster Ingestion App")
    st.write("Please enter the password to continue.")

    if pwd and pwd != st.secrets["app_password"]:
        st.error("Incorrect password")

    st.stop()

# If correct password, continue with app
st.success("Access granted.")
st.header("Upload Rosters")



# Load .env locally if SUPABASE_URL not in env
if "SUPABASE_URL" not in os.environ:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)

def get_supabase_client() -> Client:
    # For Streamlit Cloud: use st.secrets; locally: use env vars from .env
    url = os.getenv("SUPABASE_URL") or st.secrets["supabase"]["url"]
    key = os.getenv("SUPABASE_KEY") or st.secrets["supabase"]["key"]
    return create_client(url, key)


def extract_date_from_filename(
    fname: str,
    date_patterns: list[dict] | None = None,
    allow_fuzzy: bool = False
) -> date | None:
    default_patterns = [
        {'regex': r'(\d{4}-\d{1,2}-\d{1,2})', 'formats': ['%Y-%m-%d']},
        {'regex': r'(\d{1,2}[.-]\d{1,2}[.-]\d{4})', 'formats': ['%m.%d.%Y', '%m-%d-%Y']},
        {'regex': r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 'formats': ['%m/%d/%Y']},
        {'regex': r'(\d{4}[.-]\d{1,2}[.-]\d{1,2})', 'formats': ['%Y.%m.%d', '%Y-%m-%d']},
    ]
    patterns = date_patterns if date_patterns is not None else default_patterns

    for pat_info in patterns:
        pat = pat_info.get('regex')
        m = re.search(pat, fname) if pat else None
        if not m:
            continue
        date_str = m.group(1)
        for fmt in pat_info.get('formats', []):
            try:
                parsed = datetime.strptime(date_str, fmt).date()
                return parsed
            except ValueError:
                continue

    # Optional fuzzy parsing if desired
    try:
        from dateutil.parser import parse as fuzzy_parse
        _HAS_DATEUTIL = True
    except ImportError:
        _HAS_DATEUTIL = False
    if allow_fuzzy and _HAS_DATEUTIL:
        if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
                     fname, flags=re.IGNORECASE):
            try:
                dt = fuzzy_parse(fname, fuzzy=True, dayfirst=False)
                return dt.date()
            except Exception:
                pass
    return None

def clean_roster_generic(
    df: pd.DataFrame,
    filename: str,
    keep_positions=None,
    date_regex=None,
    extra_date_patterns: list[dict] | None = None,
    allow_fuzzy_date: bool = False
) -> pd.DataFrame:
    """
    Clean a roster dataframe loaded from Excel (header=None).
    filename is used for date parsing.
    """
    # Drop first column if exists
    if df.shape[1] >= 1:
        df2 = df.iloc[:, 1:].copy()
    else:
        df2 = df.copy()
    df2.columns = [f"column_{i+1}" for i in range(df2.shape[1])]
    df2 = df2.replace(r'^\s*$', pd.NA, regex=True)

    # Extract Unit
    if {'column_1', 'column_2', 'column_3'}.issubset(df2.columns):
        unit_rows = df2['column_2'].isna() & df2['column_3'].isna()
        df2['Unit'] = df2['column_1'].where(unit_rows).ffill()
    else:
        df2['Unit'] = pd.NA

    # Drop repeated headers
    mask = pd.Series(True, index=df2.index)
    if 'column_1' in df2.columns and 'column_2' in df2.columns:
        col1_strip = df2['column_1'].astype(str).str.strip().str.upper()
        col2_strip = df2['column_2'].astype(str).str.strip().str.upper()
        mask &= ~((col1_strip == 'RANK') & (col2_strip == 'ID'))
    if 'column_2' in df2.columns and 'column_3' in df2.columns:
        mask &= ~(df2['column_2'].isna() & df2['column_3'].isna())
    df2 = df2.loc[mask].reset_index(drop=True)

    if 'column_1' in df2.columns:
        df2['column_1'] = df2['column_1'].ffill()
        df2 = df2[df2['column_1'].notna()].reset_index(drop=True)

    # Keep specific columns
    if keep_positions is None:
        keep_positions = [1, 2, 3, 5, 6, 7, 8]
    keep_cols = ['Unit']
    for pos in keep_positions:
        col = f"column_{pos}"
        if col in df2.columns:
            keep_cols.append(col)
    df2 = df2.loc[:, keep_cols].copy()

    # Clean up types
    if 'column_1' in df2.columns:
        df2['column_1'] = df2['column_1'].astype(str).str.replace(r'^\.+', '', regex=True).str.strip()
    if 'column_2' in df2.columns:
        df2['column_2'] = df2['column_2'].astype(str)
    if 'column_6' in df2.columns:
        df2['column_6'] = pd.to_datetime(df2['column_6'], format='%H:%M', errors='coerce').dt.time
    if 'column_7' in df2.columns:
        df2['column_7'] = pd.to_datetime(df2['column_7'], format='%H:%M', errors='coerce').dt.time
    if 'column_8' in df2.columns:
        df2['column_8'] = pd.to_numeric(df2['column_8'], errors='coerce')

    # Parse Date from filename
    parsed_date = None
    if date_regex:
        m = re.search(date_regex, filename)
        if m:
            date_str = m.group(1)
            parsed_ts = pd.to_datetime(date_str, errors='coerce', infer_datetime_format=True)
            if not pd.isna(parsed_ts):
                parsed_date = parsed_ts.date()
    if parsed_date is None:
        pd_f = extract_date_from_filename(filename, date_patterns=extra_date_patterns, allow_fuzzy=allow_fuzzy_date)
        if pd_f:
            parsed_date = pd_f
    if parsed_date:
        df2['Date'] = parsed_date
    else:
        df2['Date'] = pd.NaT

    # Reorder columns
    final_order = ['Unit'] + [f"column_{pos}" for pos in keep_positions] + ['Date']
    final_cols = [c for c in final_order if c in df2.columns]
    df2 = df2.loc[:, final_cols]

    # Rename sequentially to column_1..column_N
    final_mapping = {orig: f"column_{i+1}" for i, orig in enumerate(final_cols)}
    df2 = df2.rename(columns=final_mapping)
    return df2

def rename_and_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename generic columns to meaningful names and convert types.
    """
    rename_map = {
        "column_1": "division",
        "column_2": "rank",
        "column_3": "member_id",
        "column_4": "name",
        "column_5": "code",
        "column_6": "start",
        "column_7": "through",
        "column_8": "hours",
        "column_9": "roster_date"
    }
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df2 = df.rename(columns=rename_map)

    # Drop rows without valid member_id
    if "member_id" in df2.columns:
        df2 = df2[df2["member_id"].notna() & df2["member_id"].astype(str).str.strip().ne("")]

    # Convert types
    import datetime as _dt
    if "hours" in df2.columns:
        df2["hours"] = pd.to_numeric(df2["hours"], errors="coerce")
    for tcol in ["start", "through"]:
        if tcol in df2.columns:
            df2[tcol] = df2[tcol].apply(
                lambda x: x.isoformat() if isinstance(x, _dt.time) else (None if pd.isna(x) else str(x))
            )
    if "roster_date" in df2.columns:
        df2["roster_date"] = df2["roster_date"].apply(
            lambda d: d.isoformat() if isinstance(d, _dt.date) else None 
        )

    df2 = df2.where(pd.notnull(df2), None)
    return df2

def already_processed(filename: str) -> bool:
    supabase = get_supabase_client()
    res = supabase.table("processed_uploads")\
        .select("id")\
        .eq("filename", filename)\
        .eq("status", "success")\
        .limit(1)\
        .execute()
    err = getattr(res, "error", None)
    if err:
        st.warning(f"Warning checking processed_uploads: {err}")
        return False
    data = getattr(res, "data", None)
    return bool(isinstance(data, list) and data)

def log_processed_upload(filename: str, row_count: int | None, status: str, error_message: str | None = None):
    supabase = get_supabase_client()
    now_et = datetime.now(ZoneInfo("America/New_York"))
    record = {
        "filename": filename,
        "ingested_at": now_et.isoformat(),
        "row_count": row_count,
        "status": status,
        "error_message": error_message
    }
    res = supabase.table("processed_uploads").insert(record).execute()
    err = getattr(res, "error", None)
    if err:
        st.warning(f"Failed to log processed_uploads entry: {err}")

def push_to_supabase(df: pd.DataFrame) -> int:
    supabase = get_supabase_client()
    records = df.to_dict(orient="records")
    res = supabase.table("roster_data").insert(records).execute()
    err = getattr(res, "error", None)
    if err:
        raise RuntimeError(f"Supabase insert error: {err}")
    data = getattr(res, "data", None)
    if isinstance(data, list):
        return len(data)
    return len(records)

# Streamlit UI
st.title("Roster Report Ingestion")

st.markdown("""
Upload one or more Excel roster reports. The app will clean each roster, push rows to database, and log each upload. <br><br>
**Excel file format: Roster Report.M.D.Y.xlsx** (ex. Roster Report.6.10.2025.xlsx).<br><br>

""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Choose one or more Excel files",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

force = st.checkbox("Force reprocess even if filename was processed before", value=False)

if uploaded_files:
    if st.button("Process and upload all"):
        summary = []
        for uploaded_file in uploaded_files:
            filename = Path(uploaded_file.name).name
            st.write(f"---\n**File:** {filename}")
            if not force and already_processed(filename):
                st.warning(f"Skipping '{filename}' (already processed).")
                summary.append((filename, "skipped", 0))
                continue
            try:
                df_raw = pd.read_excel(uploaded_file, header=None)
                #st.write("Raw data preview:")
                #st.dataframe(df_raw.head())

                df_clean = clean_roster_generic(df_raw, filename)
                #st.write("Cleaned preview:")
                #st.dataframe(df_clean.head())

                df_final = rename_and_type(df_clean)
                st.write("Final preview:")
                st.dataframe(df_final.head())

                st.info("Pushing to Supabase...")
                row_count = push_to_supabase(df_final)
                st.success(f"Inserted {row_count} rows for '{filename}'.")
                log_processed_upload(filename=filename, row_count=row_count, status="success", error_message=None)
                summary.append((filename, "success", row_count))
            except Exception as e:
                err_msg = str(e)
                st.error(f"Error processing '{filename}': {err_msg}")
                log_processed_upload(filename=filename, row_count=None, status="error", error_message=err_msg)
                summary.append((filename, "error", 0))
        df_summary = pd.DataFrame(summary, columns=["filename", "status", "row_count"])
        st.write("## Summary")
        st.dataframe(df_summary)

if st.checkbox("Show recent processed uploads"):
    supabase = get_supabase_client()
    res = supabase.table("processed_uploads")\
        .select("*")\
        .order("ingested_at", desc=True)\
        .limit(20)\
        .execute()
    err = getattr(res, "error", None)
    if err:
        st.error(f"Error fetching processed_uploads: {err}")
    else:
        data = getattr(res, "data", None)
        if isinstance(data, list):
            df_hist = pd.DataFrame(data)
            if "ingested_at" in df_hist.columns:
                df_hist["ingested_at"] = pd.to_datetime(df_hist["ingested_at"])
            st.dataframe(df_hist)
        else:
            st.write(data)
