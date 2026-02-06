import streamlit as st
import requests
import pandas as pd
from io import BytesIO


# ================== CONFIG ==================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]


# ================== GITHUB HELPERS ==================
def github_get(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []

    return r.json()


# ================== DATA HELPERS ==================
def get_available_dates():
    folders = github_get("attendance")

    dates = [
        f["name"]
        for f in folders
        if f.get("type") == "dir"
    ]

    return sorted(dates, reverse=True)


def get_csv_files_for_date(date):
    files = github_get(f"attendance/{date}")

    return [
        f for f in files
        if f.get("name", "").endswith(".csv")
    ]


# ================== UI ==================
st.set_page_config(
    page_title="LAVA",
    layout="wide"
)

st.title("📚 Lecture Attendance View Archive (LAVA)")


# ================== DATE SELECTION ==================
dates = get_available_dates()

if not dates:
    st.info("No attendance records available.")
    st.stop()

selected_date = st.selectbox(
    "📅 Select Date",
    dates
)


# ================== LOAD FILES ==================
csv_files = get_csv_files_for_date(selected_date)

if not csv_files:
    st.warning("No attendance found for this date.")
    st.stop()


# ================== GLOBAL SEARCH ==================
query = st.text_input(
    "🔍 Search by course code, department, or time"
)

if query:
    csv_files = [
        f for f in csv_files
        if query.lower() in f["name"].lower()
    ]

if not csv_files:
    st.warning("No matching attendance found.")
    st.stop()


# ================== FILE SELECTION ==================
file_names = [f["name"] for f in csv_files]

selected_file = st.selectbox(
    "📄 Select Attendance",
    file_names
)


# ================== VIEW ATTENDANCE ==================
file_info = next(
    f for f in csv_files
    if f["name"] == selected_file
)

csv_bytes = requests.get(file_info["download_url"]).content
df = pd.read_csv(BytesIO(csv_bytes))


st.subheader("Attendance Preview")

st.write(f"Total Students: {len(df)}")

st.dataframe(
    df,
    use_container_width=True
)


# ================== DOWNLOAD ==================
st.download_button(
    "📥 Download CSV",
    csv_bytes,
    file_name=selected_file,
    mime="text/csv"
)


# ================== FOOTER ==================
st.divider()

st.caption(
    "❤️ Made with love by EPE2025/26. FODC. "
    "Support: wa.me/2348118429150"
)
