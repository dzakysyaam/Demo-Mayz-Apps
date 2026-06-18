import base64
from pathlib import Path
from typing import Dict, List

import streamlit as st

from src.config import LOGO_FILE, STYLE_FILE

STEPS = [
    ("upload", "Upload Template"),
    ("read", "Read Accounts"),
    ("scrape", "Scrape Instagram"),
    ("detail", "Extract Detail"),
    ("excel", "Build Excel"),
    ("download", "Download Output"),
]

def load_css():
    if STYLE_FILE.exists():
        st.markdown(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def sidebar_brand():
    with st.sidebar:
        if LOGO_FILE.exists():
            st.image(str(LOGO_FILE), use_container_width=True)
        else:
            st.markdown("<div class='brand-fallback'>Mayz</div>", unsafe_allow_html=True)
        st.markdown("<div class='side-title'>Mayz</div>", unsafe_allow_html=True)
        st.caption("Pelaporan publikasi Kanwil DJPb")
        st.divider()
        st.markdown("**Mode POC**")
        st.caption("Public scraping tanpa API, login, proxy, atau bypass.")

def render_header():
    st.markdown(
        """
        <div class="hero">
            <div>
                <div class="eyebrow">DJPb Social Media Reporting</div>
                <h1>Mayz</h1>
                <p>Website bantu untuk upload template, menjalankan scraping publik Instagram, membaca metadata postingan, dan menghasilkan laporan Excel yang siap direview.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_flow(current: str, done: List[str]):
    html = "<div class='flow-board'>"
    for index, (key, label) in enumerate(STEPS):
        state = "pending"
        if key in done:
            state = "done"
        if key == current:
            state = "active"
        html += f"<div class='flow-node {state}'><div class='node-icon'>{index + 1}</div><div class='node-title'>{label}</div><div class='node-status'>{state}</div></div>"
        if index < len(STEPS) - 1:
            html += f"<div class='flow-line {state}'></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_metrics(summary: Dict):
    items = [
        ("Akun", summary.get("accounts", 0)),
        ("Link terbaca", summary.get("links", 0)),
        ("Tanggal", summary.get("dates", 0)),
        ("Caption", summary.get("captions", 0)),
        ("Like", summary.get("likes", 0)),
        ("Comment", summary.get("comments", 0)),
        ("Gagal", summary.get("failed", 0)),
    ]
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

def status_box(kind: str, text: str):
    st.markdown(f"<div class='status-box {kind}'>{text}</div>", unsafe_allow_html=True)