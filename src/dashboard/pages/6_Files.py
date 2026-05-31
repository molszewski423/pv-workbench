"""
PV AI Workbench — File Browser

View and download all generated reports, data files, and analysis outputs.
"""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(
    page_title="Files — PV AI Workbench",
    page_icon="📁",
    layout="wide",
)

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
from auth import require_auth, auth_sidebar
require_auth()

with st.sidebar:
    auth_sidebar()

st.title("📁 Generated Files")
st.caption("Browse and download analysis outputs, reports, and data files.")

# ── Directories to scan ──────────────────────────────────────────────────────

HOME = Path.home()

SEARCH_DIRS = [
    (Path("/app/output"),                            "Workbench Output"),
    (HOME / "Desktop" / "vancomycin_pv_analysis",   "Vancomycin Analysis"),
]

# File types to surface
INCLUDE_SUFFIXES = {
    ".pdf":  ("PDF Report",    "📄"),
    ".json": ("JSON Data",     "📊"),
    ".png":  ("Chart / Image", "🖼️"),
    ".md":   ("Markdown",      "📝"),
    ".csv":  ("CSV Data",      "📋"),
    ".html": ("HTML Report",   "🌐"),
    ".txt":  ("Text File",     "📃"),
    ".xlsx": ("Excel",         "📋"),
}

# ── Scan and collect files ───────────────────────────────────────────────────

@st.cache_data(ttl=15)
def _scan_files() -> list[dict]:
    results = []
    seen = set()
    for base_dir, label in SEARCH_DIRS:
        if not base_dir.exists():
            continue
        # For Desktop, only list direct children (not recursive) to avoid noise
        pattern = "*" if base_dir == HOME / "Desktop" else "**/*"
        for f in sorted(base_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            if f.suffix.lower() not in INCLUDE_SUFFIXES:
                continue
            if f.resolve() in seen:
                continue
            seen.add(f.resolve())
            stat = f.stat()
            results.append({
                "path":     f,
                "name":     f.name,
                "dir":      label,
                "suffix":   f.suffix.lower(),
                "size_kb":  stat.st_size / 1024,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            })
    return results


files = _scan_files()

if not files:
    st.warning("No output files found. Run an analysis to generate files.")
    st.stop()

# ── Filters ──────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns([2, 2, 3])

with col_f1:
    all_dirs = ["All"] + sorted({f["dir"] for f in files})
    dir_filter = st.selectbox("Directory", all_dirs)

with col_f2:
    type_options = ["All"] + sorted({INCLUDE_SUFFIXES[f["suffix"]][0] for f in files})
    type_filter = st.selectbox("File type", type_options)

with col_f3:
    search = st.text_input("Search filename", placeholder="e.g. vancomycin, report, chart")

with col_f3:
    if st.button("↻ Refresh", key="refresh_files"):
        st.cache_data.clear()
        st.rerun()

# Apply filters
filtered = files
if dir_filter != "All":
    filtered = [f for f in filtered if f["dir"] == dir_filter]
if type_filter != "All":
    filtered = [f for f in filtered if INCLUDE_SUFFIXES[f["suffix"]][0] == type_filter]
if search.strip():
    q = search.strip().lower()
    filtered = [f for f in filtered if q in f["name"].lower()]

st.caption(f"Showing {len(filtered)} of {len(files)} files")
st.markdown("---")

# ── File list ────────────────────────────────────────────────────────────────

if not filtered:
    st.info("No files match the current filters.")
    st.stop()

# Group by directory
from itertools import groupby

by_dir = {}
for f in filtered:
    by_dir.setdefault(f["dir"], []).append(f)

for dir_label, dir_files in by_dir.items():
    st.markdown(f"#### {dir_label}")

    for entry in dir_files:
        suffix = entry["suffix"]
        type_label, icon = INCLUDE_SUFFIXES.get(suffix, ("File", "📄"))
        size_str = (
            f"{entry['size_kb'] / 1024:.1f} MB"
            if entry["size_kb"] > 1024
            else f"{entry['size_kb']:.0f} KB"
        )
        modified_str = entry["modified"].strftime("%Y-%m-%d %H:%M")

        col_icon, col_name, col_meta, col_dl = st.columns([0.5, 4, 2, 1.5])

        with col_icon:
            st.markdown(f"### {icon}")

        with col_name:
            st.markdown(f"**{entry['name']}**")
            st.caption(str(entry["path"].parent))

        with col_meta:
            st.caption(f"{type_label} · {size_str}")
            st.caption(f"Modified: {modified_str}")

        with col_dl:
            try:
                file_bytes = entry["path"].read_bytes()
                mime_map = {
                    ".pdf":  "application/pdf",
                    ".json": "application/json",
                    ".png":  "image/png",
                    ".md":   "text/markdown",
                    ".csv":  "text/csv",
                    ".html": "text/html",
                    ".txt":  "text/plain",
                    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
                mime = mime_map.get(suffix, "application/octet-stream")
                st.download_button(
                    label="Download",
                    data=file_bytes,
                    file_name=entry["name"],
                    mime=mime,
                    key=str(entry["path"]),
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Read error: {e}")

        # Preview for supported types
        if suffix == ".png":
            with st.expander("Preview", expanded=False):
                st.image(str(entry["path"]))

        elif suffix in (".md", ".txt"):
            with st.expander("Preview", expanded=False):
                try:
                    content = entry["path"].read_text(errors="replace")
                    st.markdown(content[:4000] + ("…" if len(content) > 4000 else ""))
                except Exception as e:
                    st.caption(f"Preview unavailable: {e}")

        elif suffix == ".json":
            with st.expander("Preview", expanded=False):
                try:
                    import json
                    content = json.loads(entry["path"].read_text())
                    st.json(content)
                except Exception as e:
                    st.caption(f"Preview unavailable: {e}")

        st.divider()
