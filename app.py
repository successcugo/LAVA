from __future__ import annotations

import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# ── Config from secrets ───────────────────────────────────────────────────────
# Secrets expected (same as ULAS):
#   GITHUB_PAT   = "github_pat_..."
#   LAVA_OWNER   = "successcugo"
#   LAVA_REPO    = "LAVA"

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
    """List contents of a path in the LAVA repo. Cached for 60s."""
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []
    data = r.json()
    return data if isinstance(data, list) else []

@st.cache_data(ttl=300, show_spinner=False)
def fetch_csv(download_url: str) -> bytes:
    """Download a CSV file. Cached for 5 minutes."""
    r = requests.get(download_url, headers=HEADERS, timeout=10)
    return r.content


def list_dirs(path: str) -> list[str]:
    return sorted([f["name"] for f in gh_list(path) if f.get("type") == "dir"])

def list_csvs(path: str) -> list[dict]:
    return [f for f in gh_list(path) if f.get("name","").endswith(".csv")]


# ── Navigation: School → Department → File ────────────────────────────────────
# Structure in LAVA: attendances/SCHOOL_ABBR/Department_Name/COURSECODE_Dept_Date.csv

ROOT = "attendances"

schools = list_dirs(ROOT)

if not schools:
    st.info("No attendance records have been pushed to LAVA yet.")
    st.caption("Records appear here automatically when course reps end attendance sessions in ULAS.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown("### 🔍 Browse Records")

col1, col2, col3 = st.columns(3)

with col1:
    selected_school = st.selectbox("School", ["— All Schools —"] + schools)

with col2:
    if selected_school != "— All Schools —":
        depts = list_dirs(f"{ROOT}/{selected_school}")
    else:
        # Aggregate all departments across all schools
        depts = []
        for s in schools:
            depts += list_dirs(f"{ROOT}/{s}")
        depts = sorted(set(depts))
    selected_dept = st.selectbox("Department", ["— All Departments —"] + depts)

with col3:
    search = st.text_input("🔍 Search by course code or date", placeholder="e.g. CSC301 or 2025-01")

# ── Collect matching CSV files ────────────────────────────────────────────────
all_files: list[dict] = []   # each entry: {name, download_url, school, dept}

target_schools = [selected_school] if selected_school != "— All Schools —" else schools

for sch in target_schools:
    target_depts = (
        [selected_dept] if selected_dept != "— All Departments —"
        else list_dirs(f"{ROOT}/{sch}")
    )
    for dep in target_depts:
        for f in list_csvs(f"{ROOT}/{sch}/{dep}"):
            all_files.append({
                "name":         f["name"],
                "download_url": f["download_url"],
                "school":       sch,
                "dept":         dep,
                "path":         f"{ROOT}/{sch}/{dep}/{f['name']}",
            })

# Apply text search
if search.strip():
    q = search.strip().lower()
    all_files = [f for f in all_files if q in f["name"].lower() or q in f["dept"].lower()]

if not all_files:
    st.warning("No attendance records match your filters.")
    st.stop()

# ── Summary stats ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(f'<div class="stat-box"><div class="num">{len(all_files)}</div><div class="lbl">Records Found</div></div>', unsafe_allow_html=True)
with s2:
    unique_depts = len(set(f["dept"] for f in all_files))
    st.markdown(f'<div class="stat-box"><div class="num">{unique_depts}</div><div class="lbl">Departments</div></div>', unsafe_allow_html=True)
with s3:
    unique_schools = len(set(f["school"] for f in all_files))
    st.markdown(f'<div class="stat-box"><div class="num">{unique_schools}</div><div class="lbl">Schools</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── File selector ─────────────────────────────────────────────────────────────
st.markdown("### 📄 Select Attendance Record")

file_labels = {
    f"{f['school']} / {f['dept']} / {f['name']}": f
    for f in sorted(all_files, key=lambda x: x["name"], reverse=True)
}

selected_label = st.selectbox("Attendance file", list(file_labels.keys()))
selected_file  = file_labels[selected_label]

# ── Parse filename for display: COURSECODE_Dept_YYYY-MM-DD_HH-MM.csv ─────────
parts    = selected_file["name"].replace(".csv","").split("_")
course   = parts[0] if parts else "—"
date_str = parts[-2] if len(parts) >= 2 else "—"
time_str = parts[-1].replace("-",":") if len(parts) >= 3 else "—"

st.markdown(f"""<div class="info-card">
    <b>Course:</b> {course} &nbsp;|&nbsp;
    <b>Department:</b> {selected_file['dept'].replace('_',' ')} &nbsp;|&nbsp;
    <b>School:</b> {selected_file['school']} &nbsp;|&nbsp;
    <b>Date:</b> {date_str} &nbsp;|&nbsp;
    <b>Time:</b> {time_str}
</div>""", unsafe_allow_html=True)

# ── Load and display CSV ──────────────────────────────────────────────────────
with st.spinner("Loading attendance record..."):
    csv_bytes = fetch_csv(selected_file["download_url"])

try:
    df = pd.read_csv(BytesIO(csv_bytes))
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

st.markdown(f"### Attendance — {course} ({len(df)} students)")
st.dataframe(df, use_container_width=True, hide_index=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.download_button(
    "📥 Download CSV",
    csv_bytes,
    file_name=selected_file["name"],
    mime="text/csv",
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("❤️ Made with love by EPE2025/26. FODC. Support: wa.me/2348118429150")
