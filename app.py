from __future__ import annotations

import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# ── Secrets ───────────────────────────────────────────────────────────────────
TOKEN = st.secrets["GITHUB_PAT"]
REPO  = f"{st.secrets['LAVA_OWNER']}/{st.secrets['LAVA_REPO']}"

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LAVA — Lecture Attendance Archive",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #7b0000 0%, #c0392b 100%);
    border-radius: 16px; padding: 2rem; text-align: center;
    color: white; margin-bottom: 2rem;
    box-shadow: 0 4px 20px rgba(123,0,0,0.3);
}
.hero h1 { font-size: 2rem; font-weight: 900; margin: 0; }
.hero .sub { opacity: 0.85; margin-top: 0.3rem; font-size: 0.95rem; }
.hero .badge {
    display: inline-block; background: rgba(255,255,255,0.2);
    border-radius: 20px; padding: 3px 14px; font-size: 0.8rem; margin-top: 0.6rem;
}
.info-card {
    background: rgba(192, 57, 43, 0.08);
    border-left: 4px solid #c0392b;
    border-radius: 0 8px 8px 0;
    padding: 0.7rem 1rem; margin: 0.5rem 0;
    font-size: 0.9rem; color: inherit;
}
.info-card b { color: #c0392b; }
.stat-box {
    background: rgba(192, 57, 43, 0.07);
    border: 1px solid rgba(192, 57, 43, 0.2);
    border-radius: 10px; padding: 1rem;
    text-align: center; color: inherit;
}
.stat-box .num { font-size: 2rem; font-weight: 900; color: #c0392b; }
.stat-box .lbl { font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }
div[data-testid="stForm"] {
    border: 1.5px solid rgba(128,128,128,0.3);
    border-radius: 12px; padding: 1.2rem 1.2rem 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>📚 LAVA</h1>
    <div class="sub">Lecture Attendance Viewing Archive</div>
    <div class="badge">Federal University of Technology, Owerri</div>
</div>
""", unsafe_allow_html=True)


# ── GitHub helpers ────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def gh_list(path: str) -> list[dict]:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r   = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []
    data = r.json()
    return data if isinstance(data, list) else []

@st.cache_data(ttl=300, show_spinner=False)
def fetch_csv(download_url: str) -> bytes:
    return requests.get(download_url, headers=HEADERS, timeout=10).content

def list_dirs(path: str) -> list[str]:
    return sorted([f["name"] for f in gh_list(path) if f.get("type") == "dir"], reverse=True)

def list_csvs(path: str) -> list[dict]:
    return [f for f in gh_list(path) if f.get("name", "").endswith(".csv")]


# ── New structure: attendances/(YYYY-MM-DD)/SCHOOLCOURSEABBRLEVEL_DATE.csv ────
ROOT = "attendances"

dates = list_dirs(ROOT)

if not dates:
    st.info("No attendance records have been pushed to LAVA yet.")
    st.caption("Records appear here automatically when course reps end attendance sessions in ULAS.")
    st.stop()

# ── Date selector ─────────────────────────────────────────────────────────────
st.markdown("### 📅 Select Date")
selected_date = st.selectbox(
    "Date",
    dates,
    format_func=lambda d: d,   # already YYYY-MM-DD, sorts newest first
)

# ── Load all CSV files for that date ─────────────────────────────────────────
with st.spinner(f"Loading records for {selected_date}..."):
    all_files = list_csvs(f"{ROOT}/{selected_date}")

if not all_files:
    st.warning(f"No attendance records found for {selected_date}.")
    st.stop()

# ── Search / filter ───────────────────────────────────────────────────────────
st.markdown("### 🔍 Filter")
search = st.text_input(
    "Search by course code, school, or abbreviation",
    placeholder="e.g. CSC301  or  EEE  or  SEET",
)

filtered = all_files
if search.strip():
    q        = search.strip().lower()
    filtered = [f for f in all_files if q in f["name"].lower()]

if not filtered:
    st.warning("No records match your search.")
    st.stop()

# ── Stats ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
s1, s2 = st.columns(2)
with s1:
    st.markdown(
        f'<div class="stat-box"><div class="num">{len(filtered)}</div>'
        f'<div class="lbl">Records for {selected_date}</div></div>',
        unsafe_allow_html=True,
    )
with s2:
    # Count unique course codes (first segment before digits, rough heuristic)
    courses = set()
    for f in filtered:
        # Filename: SCHOOLCOURSECODEABBRlevel_date.csv
        # Course code starts after school abbr (4-5 chars) — extract via digits
        name = f["name"].replace(".csv", "")
        # Find where digits start (course codes have digits like CSC301)
        for i, ch in enumerate(name):
            if ch.isdigit():
                # Back up to grab letters before this digit group
                courses.add(name[max(0,i-3):i+3])
                break
    st.markdown(
        f'<div class="stat-box"><div class="num">{len(courses)}</div>'
        f'<div class="lbl">Courses</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── File selector ─────────────────────────────────────────────────────────────
st.markdown("### 📄 Select Attendance Record")

# Parse filename for readable label
# Format: SEETCSC301EEE300_2026-01-15.csv
def parse_filename(name: str) -> str:
    """Turn SEETCSC301EEE300_2026-01-15.csv into a readable label."""
    try:
        base   = name.replace(".csv", "")
        # Split on underscore — left part is identifiers, right is date
        parts  = base.split("_")
        idents = parts[0]   # e.g. SEETCSC301EEE300
        date   = parts[1] if len(parts) > 1 else ""
        # School abbr is first 4-5 uppercase letters before a digit
        school = ""
        rest   = idents
        for i, ch in enumerate(idents):
            if ch.isdigit():
                school = idents[:max(1, i-6)]
                rest   = idents[len(school):]
                break
        return f"{date}  ·  {school}  ·  {rest}"
    except Exception:
        return name

file_labels = {parse_filename(f["name"]): f for f in sorted(filtered, key=lambda x: x["name"])}

selected_label = st.selectbox("Attendance file", list(file_labels.keys()))
selected_file  = file_labels[selected_label]
filename       = selected_file["name"]

# ── Info card ─────────────────────────────────────────────────────────────────
# Filename format: SCHOOLCOURSECODEABBRlevel_date.csv
# e.g. SEETCSC301EEE300_2026-01-15.csv
base = filename.replace(".csv", "")
st.markdown(f"""<div class="info-card">
    <b>File:</b> {filename} &nbsp;|&nbsp;
    <b>Date:</b> {selected_date}
</div>""", unsafe_allow_html=True)

# ── Load and display CSV ──────────────────────────────────────────────────────
with st.spinner("Loading attendance record..."):
    csv_bytes = fetch_csv(selected_file["download_url"])

try:
    df = pd.read_csv(BytesIO(csv_bytes))
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

st.markdown(f"### Attendance Record — {base}  ({len(df)} students)")
st.dataframe(df, use_container_width=True, hide_index=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.download_button(
    "📥 Download CSV",
    csv_bytes,
    file_name=filename,
    mime="text/csv",
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("❤️ Made with love by EPE2025/26. FODC. Support: wa.me/2348118429150")
