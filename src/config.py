from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
STYLE_FILE = BASE_DIR / "static" / "style.css"
LOGO_FILE = BASE_DIR / "assets" / "logo" / "mayz.png"
TEMPLATE_FILE = DATA_DIR / "template_mayz_djpb.xlsx"

SHEET_SOURCE = "DJPb"
SHEET_OUTPUT = "DJPb"
SHEET_RAW = "Raw_Scraping"

DEFAULT_PERIOD_START = "2026-06-08"
DEFAULT_PERIOD_END = "2026-06-13"

BASE_HEADERS = [
    "No.",
    "Nama Kanwil",
    "Nama Unit Eselon III",
    "Tanggal Postingan",
    "Jenis Kegiatan",
    "Judul Postingan",
    "Link",
    "Jenis Media Sosial",
    "Jumlah Reach / Audiens",
    "No. Agenda Setting",
    "Topik Agenda Setting",
]

EXTRA_FIELD_MAP = {
    "Like Count": "like_count",
    "Comment Count": "comment_count",
    "Total Engagement": "total_engagement",
    "Source Unique ID": "shortcode",
    "Media Type": "media_type",
    "Status Scraping": "status_scraping",
    "Status Periode": "status_periode",
    "Catatan": "catatan",
}

def prepare_folders():
    DATA_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)