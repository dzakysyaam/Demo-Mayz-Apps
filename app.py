import asyncio
import sys
import subprocess
from datetime import datetime

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import pandas as pd
import streamlit as st

from src.config import EXPORT_DIR, TEMPLATE_FILE, prepare_folders
from src.excel_builder import build_output, save_output
from src.parser import load_accounts_from_excel
from src.scraper import run_scraping
from src.ui import load_css, render_flow, render_header, render_metrics, sidebar_brand, status_box


st.set_page_config(
    page_title="Mayz",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def ensure_playwright_browser():
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)
    
prepare_folders()
load_css()
sidebar_brand()
render_header()

browser_ready, browser_message = ensure_playwright_browser()

if not browser_ready:
    status_box(
        "error",
        f"Browser Chromium Playwright belum siap di environment deployment: {browser_message}",
    )
def init_state():
    defaults = {
        "flow_current": "upload",
        "flow_done": [],
        "result_bytes": None,
        "result_rows": [],
        "summary": None,
        "last_log": "",
        "is_stopped": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_result_state():
    st.session_state.result_bytes = None
    st.session_state.result_rows = []
    st.session_state.summary = None
    st.session_state.last_log = ""
    st.session_state.is_stopped = False


def update_flow(current, done=None):
    if done is None:
        done = st.session_state.flow_done

    st.session_state.flow_current = current
    st.session_state.flow_done = done

    with flow_slot.container():
        render_flow(current, done)


def build_preview_accounts(accounts):
    return pd.DataFrame([
        {
            "No": account.no,
            "Nama Kanwil": account.nama_kanwil,
            "URL Akun": account.url_akun,
        }
        for account in accounts
    ])


def build_preview_rows(rows):
    return pd.DataFrame([
        {
            "Nama Kanwil": row.nama_kanwil,
            "Tanggal": row.tanggal_postingan,
            "Caption": row.caption,
            "Link": row.post_url,
            "Like": row.like_count,
            "Comment": row.comment_count,
            "Engagement": row.total_engagement,
            "Status": row.status_scraping,
            "Catatan": row.catatan,
        }
        for row in rows
        if row.post_url
    ])


init_state()

flow_slot = st.empty()

with flow_slot.container():
    render_flow(st.session_state.flow_current, st.session_state.flow_done)


st.markdown(
    "<div class='section-title'>Upload master akun Instagram</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    uploaded_file = st.file_uploader(
        "Drag and drop file master akun Instagram Kanwil di sini, atau klik untuk memilih file.",
        type=["xlsx"],
        help="File digunakan sebagai sumber akun Instagram yang akan discrape. Pastikan terdapat Nama Kanwil dan URL Instagram.",
    )

with right:
    st.markdown(
        """
        <div class='soft-card'>
            Contoh file master akun tersedia untuk uji coba. Isi daftar Nama Kanwil dan URL Instagram pada sheet DJPb.
            File ini digunakan sebagai sumber akun yang akan diproses oleh Mayz.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if TEMPLATE_FILE.exists():
        st.download_button(
            "Download contoh file master akun",
            data=TEMPLATE_FILE.read_bytes(),
            file_name="template_mayz_djpb.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


accounts = []
template_bytes = None

if uploaded_file:
    try:
        template_bytes = uploaded_file.getvalue()
        accounts = load_accounts_from_excel(template_bytes)

        update_flow("read", ["upload"])
        status_box("success", f"{len(accounts)} akun Kanwil berhasil terbaca dari file master.")

        preview_accounts = build_preview_accounts(accounts)
        st.dataframe(preview_accounts, use_container_width=True, hide_index=True)

    except Exception as exc:
        status_box("error", str(exc))


st.markdown(
    "<div class='section-title'>Konfigurasi scraping</div>",
    unsafe_allow_html=True,
)

with st.form("scrape_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        period_start = st.date_input("Periode mulai", value=datetime(2026, 6, 8))
        max_posts = st.number_input(
            "Maksimal postingan per akun",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
        )

    with col2:
        period_end = st.date_input("Periode selesai", value=datetime(2026, 6, 13))
        scrolls = st.number_input(
            "Jumlah scroll per akun",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
        )

    with col3:
        delay = st.number_input(
            "Delay antar akun",
            min_value=4.0,
            max_value=20.0,
            value=5.0,
            step=1.0,
            key="delay_between_accounts_v2",
        )
        show_browser = st.checkbox("Tampilkan browser saat scraping", value=True)

        st.markdown("**Data tambahan yang ingin dimasukkan ke output**")

    st.markdown(
        """
        <div style="
            border: 1px solid #d8e1ea;
            border-radius: 16px;
            padding: 18px 18px 8px 18px;
            background: rgba(255,255,255,.45);
            margin-bottom: 18px;
        ">
        """,
        unsafe_allow_html=True,
    )

    output_row_1 = st.columns(4)

    with output_row_1[0]:
        field_like = st.checkbox("Like Count", value=True, key="field_like_count")

    with output_row_1[1]:
        field_comment = st.checkbox("Comment Count", value=True, key="field_comment_count")

    with output_row_1[2]:
        field_engagement = st.checkbox("Total Engagement", value=True, key="field_total_engagement")

    with output_row_1[3]:
        field_unique_id = st.checkbox("Source Unique ID", value=True, key="field_source_unique_id")

    output_row_2 = st.columns(4)

    with output_row_2[0]:
        field_media_type = st.checkbox("Media Type", value=True, key="field_media_type")

    with output_row_2[1]:
        field_status_scraping = st.checkbox("Status Scraping", value=True, key="field_status_scraping")

    with output_row_2[2]:
        field_status_periode = st.checkbox("Status Periode", value=True, key="field_status_periode")

    with output_row_2[3]:
        field_catatan = st.checkbox("Catatan", value=True, key="field_catatan")

    st.markdown("</div>", unsafe_allow_html=True)

    selected_fields = []

    if field_like:
        selected_fields.append("Like Count")

    if field_comment:
        selected_fields.append("Comment Count")

    if field_engagement:
        selected_fields.append("Total Engagement")

    if field_unique_id:
        selected_fields.append("Source Unique ID")

    if field_media_type:
        selected_fields.append("Media Type")

    if field_status_scraping:
        selected_fields.append("Status Scraping")

    if field_status_periode:
        selected_fields.append("Status Periode")

    if field_catatan:
        selected_fields.append("Catatan")

    st.markdown("**Opsi proses scraping**")

    st.markdown(
        """
        <div style="
            border: 1px solid #d8e1ea;
            border-radius: 16px;
            padding: 18px 18px 8px 18px;
            background: rgba(255,255,255,.45);
            margin-bottom: 18px;
        ">
        """,
        unsafe_allow_html=True,
    )

    process_row = st.columns(3)

    with process_row[0]:
        with_detail = st.checkbox(
            "Ambil detail postingan",
            value=True,
            key="option_with_detail",
        )

    with process_row[1]:
        only_period = st.checkbox(
            "Hanya postingan masuk periode",
            value=False,
            key="option_only_period",
        )

    with process_row[2]:
        include_raw = st.checkbox(
            "Tambahkan sheet Raw_Scraping",
            value=True,
            key="option_include_raw",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**Opsi keamanan proses**")

    st.markdown(
        """
        <div style="
            border: 1px solid #d8e1ea;
            border-radius: 16px;
            padding: 18px 18px 8px 18px;
            background: rgba(255,255,255,.45);
            margin-bottom: 18px;
        ">
        """,
        unsafe_allow_html=True,
    )

    safety_row = st.columns(2)

    with safety_row[0]:
        stop_on_login = st.checkbox(
            "Hentikan jika Instagram meminta login",
            value=True,
            key="option_stop_on_login",
        )

    with safety_row[1]:
        stop_after_failed_streak = st.checkbox(
            "Hentikan jika beberapa akun berturut-turut gagal",
            value=True,
            key="option_stop_failed_streak",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    start_button = st.form_submit_button(
        "Mulai scraping",
        use_container_width=True,
    )


if start_button:
    reset_result_state()

    if not uploaded_file:
        status_box("error", "Upload file master akun terlebih dahulu.")

    elif not accounts:
        status_box("error", "Akun belum terbaca dari file master.")

    else:
        progress_bar = st.progress(0)
        log_box = st.empty()

        done = ["upload", "read"]
        update_flow("scrape", done)

        def progress(event):
            stage = event.get("stage", "scrape")
            message = event.get("message", "")

            if "index" in event and "total" in event:
                total = max(event.get("total", 1), 1)
                index = event.get("index", 1)
                value = min(index / total, 1.0)
                progress_bar.progress(value)

            st.session_state.last_log = message

            if stage == "stop":
                st.session_state.is_stopped = True
                log_box.markdown(
                    f"<div class='run-log'>{message}</div>",
                    unsafe_allow_html=True,
                )
                update_flow("scrape", done)
                return

            log_box.markdown(
                f"<div class='run-log'>{message}</div>",
                unsafe_allow_html=True,
            )

            active = "detail" if stage == "detail" else "scrape"
            update_flow(active, done)

        try:
            start_dt = datetime.combine(period_start, datetime.min.time())
            end_dt = datetime.combine(period_end, datetime.max.time()).replace(microsecond=0)

            rows = run_scraping(
                accounts=accounts,
                period_start=start_dt,
                period_end=end_dt,
                max_posts=int(max_posts),
                scrolls=int(scrolls),
                delay=float(delay),
                with_detail=with_detail,
                show_browser=show_browser,
                progress=progress,
                stop_on_login=stop_on_login,
                stop_after_failed_streak=stop_after_failed_streak,
            )

            update_flow("excel", ["upload", "read", "scrape", "detail"])

            result_bytes = build_output(
                accounts=accounts,
                rows=rows,
                selected_fields=selected_fields,
                only_period=only_period,
                include_raw=include_raw,
            )

            output_path = save_output(result_bytes, EXPORT_DIR)

            st.session_state.result_bytes = result_bytes
            st.session_state.result_rows = rows

            st.session_state.summary = {
                "accounts": len(accounts),
                "links": len([row for row in rows if row.post_url]),
                "dates": len([row for row in rows if row.tanggal_postingan is not None]),
                "captions": len([row for row in rows if row.caption]),
                "likes": len([row for row in rows if row.like_count is not None]),
                "comments": len([row for row in rows if row.comment_count is not None]),
                "failed": len([row for row in rows if not row.post_url]),
                "output": str(output_path),
            }

            progress_bar.progress(1.0)

            if st.session_state.is_stopped:
                log_box.markdown(
                    "<div class='run-log'>Proses dihentikan otomatis. File hasil sementara tetap dibuat dan bisa diunduh.</div>",
                    unsafe_allow_html=True,
                )
            else:
                log_box.markdown(
                    "<div class='run-log success'>Scraping selesai. File Excel siap diunduh.</div>",
                    unsafe_allow_html=True,
                )

            update_flow("download", ["upload", "read", "scrape", "detail", "excel"])

        except TypeError as exc:
            status_box(
                "error",
                f"Proses gagal karena parameter scraper belum sesuai. Pastikan src/scraper.py sudah versi terbaru. Detail: {exc}",
            )

        except Exception as exc:
            status_box("error", f"Proses gagal: {exc}")


if st.session_state.summary:
    st.markdown(
        "<div class='section-title'>Hasil Scraping</div>",
        unsafe_allow_html=True,
    )
    render_metrics(st.session_state.summary)


if st.session_state.result_rows:
    rows = st.session_state.result_rows
    preview_rows = build_preview_rows(rows)

    if not preview_rows.empty:
        st.dataframe(preview_rows, use_container_width=True, hide_index=True)
    else:
        status_box(
            "error",
            "Belum ada link postingan yang berhasil terbaca. Cek sheet Raw_Scraping pada file output untuk melihat alasan gagal.",
        )


if st.session_state.result_bytes:
    st.download_button(
        "Download Excel hasil pelaporan",
        data=st.session_state.result_bytes,
        file_name="Pelaporan Juni 2026_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )