import asyncio
import sys
from datetime import datetime
from typing import Callable, Dict, List, Optional

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.parser import (
    AccountRow,
    ScrapeRow,
    detect_media_type,
    extract_caption_from_meta,
    extract_shortcode,
    parse_dt_to_wib,
    parse_engagement_from_text,
    safe_text,
    status_periode,
)


def get_meta_content(page, selector: str) -> str:
    try:
        locator = page.locator(selector).first
        if locator.count() == 0:
            return ""
        return safe_text(locator.get_attribute("content", timeout=3000))
    except Exception:
        return ""


def close_instagram_prompt(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(700)
    except Exception:
        pass

    try:
        page.evaluate(
            """
            () => {
                const closeLabels = ["Close", "Tutup"];
                const svgs = Array.from(document.querySelectorAll("svg"));
                const target = svgs.find(svg => closeLabels.includes(svg.getAttribute("aria-label")));
                if (target) {
                    const clickable = target.closest("button, div[role='button']");
                    if (clickable) clickable.click();
                }
            }
            """
        )
        page.wait_for_timeout(900)
    except Exception:
        pass


def is_instagram_login_wall(page) -> bool:
    try:
        current_url = page.url.lower()

        if "/accounts/login" in current_url:
            return True

        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=3000).lower()
        except Exception:
            body_text = ""

        strong_signals = [
            "login ke instagram",
            "masuk ke instagram",
            "nomor ponsel, nama pengguna, atau email",
            "phone number, username, or email",
            "kata sandi",
            "password",
            "lupa kata sandi",
            "forgot password",
            "login dengan facebook",
            "log in with facebook",
        ]

        if any(signal in body_text for signal in strong_signals):
            return True

        username_input = page.locator("input[name='username']").count()
        password_input = page.locator("input[name='password']").count()

        if username_input > 0 and password_input > 0:
            return True

        return False
    except Exception:
        return False


def detect_blocked_or_empty_page(page) -> str:
    try:
        body_text = page.locator("body").inner_text(timeout=3000).lower()

        if "something went wrong" in body_text:
            return "Instagram menampilkan halaman Something Went Wrong"

        if "please wait a few minutes" in body_text:
            return "Instagram meminta menunggu beberapa menit"

        if "coba lagi nanti" in body_text:
            return "Instagram meminta coba lagi nanti"

        if "halaman ini tidak tersedia" in body_text:
            return "Halaman Instagram tidak tersedia"

        if "this page isn't available" in body_text:
            return "Halaman Instagram tidak tersedia"

        return ""
    except Exception:
        return ""


def collect_post_links(page, max_posts: int) -> List[str]:
    links = []

    try:
        hrefs = page.eval_on_selector_all(
            "a[href]",
            "elements => elements.map(a => a.href)"
        )
    except Exception:
        hrefs = []

    seen_shortcode = set()

    for href in hrefs:
        href = safe_text(href)

        if not href:
            continue

        if "/p/" not in href and "/reel/" not in href and "/tv/" not in href:
            continue

        shortcode = extract_shortcode(href)

        if not shortcode:
            continue

        if shortcode in seen_shortcode:
            continue

        seen_shortcode.add(shortcode)
        links.append(href)

        if len(links) >= max_posts:
            break

    return links


def get_post_detail(context, post_url: str, period_start: datetime, period_end: datetime) -> Dict:
    result = {
        "tanggal_postingan": None,
        "caption": "",
        "like_count": None,
        "comment_count": None,
        "total_engagement": None,
        "status_periode": "Perlu Cek Manual",
        "status_scraping": "Detail Failed",
        "catatan": "",
    }

    page = context.new_page()

    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        close_instagram_prompt(page)

        if is_instagram_login_wall(page):
            result["status_scraping"] = "Login Wall"
            result["catatan"] = "Instagram meminta login saat membuka detail postingan"
            return result

        time_raw = ""

        try:
            time_locator = page.locator("time").first
            if time_locator.count() > 0:
                time_raw = safe_text(time_locator.get_attribute("datetime", timeout=4000))
        except Exception:
            time_raw = ""

        tanggal = parse_dt_to_wib(time_raw)

        og_description = get_meta_content(page, 'meta[property="og:description"]')
        og_title = get_meta_content(page, 'meta[property="og:title"]')
        twitter_title = get_meta_content(page, 'meta[name="twitter:title"]')
        twitter_description = get_meta_content(page, 'meta[name="twitter:description"]')

        meta_source = og_description or twitter_description or og_title or twitter_title
        caption = extract_caption_from_meta(
            og_description,
            twitter_description,
            og_title,
            twitter_title,
        )

        like_count, comment_count = parse_engagement_from_text(meta_source)

        total_engagement = None
        if like_count is not None or comment_count is not None:
            total_engagement = (like_count or 0) + (comment_count or 0)

        result["tanggal_postingan"] = tanggal
        result["caption"] = caption
        result["like_count"] = like_count
        result["comment_count"] = comment_count
        result["total_engagement"] = total_engagement
        result["status_periode"] = status_periode(tanggal, period_start, period_end)
        result["status_scraping"] = "Detail Success"

        notes = []

        if tanggal is None:
            notes.append("Tanggal tidak terbaca")

        if not caption:
            notes.append("Caption/meta tidak terbaca")

        if like_count is None:
            notes.append("Like count tidak terbaca")

        if comment_count is None:
            notes.append("Comment count tidak terbaca")

        if notes:
            result["catatan"] = "; ".join(notes)

    except Exception as exc:
        result["status_scraping"] = "Detail Failed"
        result["catatan"] = str(exc)[:300]

    finally:
        page.close()

    return result


def build_empty_row(account: AccountRow, status: str, catatan: str) -> ScrapeRow:
    return ScrapeRow(
        nama_kanwil=account.nama_kanwil,
        url_akun=account.url_akun,
        post_url="",
        shortcode="",
        tanggal_postingan=None,
        media_type="",
        caption="",
        like_count=None,
        comment_count=None,
        total_engagement=None,
        status_periode="",
        status_scraping=status,
        catatan=catatan,
    )


def scrape_profile(
    context,
    account: AccountRow,
    max_posts: int,
    scrolls: int,
    with_detail: bool,
    period_start: datetime,
    period_end: datetime,
    total_accounts: int,
    progress: Optional[Callable] = None,
) -> List[ScrapeRow]:
    rows = []
    page = context.new_page()

    try:
        if progress:
            progress({
                "stage": "scrape",
                "message": f"Memproses {account.nama_kanwil}",
                "account": account.nama_kanwil,
            })

        page.goto(account.url_akun, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        close_instagram_prompt(page)

        if is_instagram_login_wall(page):
            rows.append(
                build_empty_row(
                    account,
                    "Login Wall",
                    "Instagram meminta login. Proses scraping publik tidak dapat dilanjutkan tanpa akses/login.",
                )
            )
            return rows

        blocked_message = detect_blocked_or_empty_page(page)
        if blocked_message:
            rows.append(
                build_empty_row(
                    account,
                    "Blocked",
                    blocked_message,
                )
            )
            return rows

        post_links = collect_post_links(page, max_posts)

        for _ in range(scrolls):
            if len(post_links) >= max_posts:
                break

            page.mouse.wheel(0, 2600)
            page.wait_for_timeout(2200)
            close_instagram_prompt(page)

            if is_instagram_login_wall(page):
                rows.append(
                    build_empty_row(
                        account,
                        "Login Wall",
                        "Instagram meminta login setelah proses scroll.",
                    )
                )
                return rows

            post_links = collect_post_links(page, max_posts)

        if not post_links:
            rows.append(
                build_empty_row(
                    account,
                    "Tidak Ada Link Terbaca",
                    "Halaman terbuka, tetapi link post/reel tidak terbaca. Kemungkinan konten belum render, terkena limit, atau struktur halaman berubah.",
                )
            )
            return rows

        for index, post_url in enumerate(post_links, start=1):
            if progress:
                progress({
                    "stage": "detail" if with_detail else "scrape",
                    "message": f"{account.nama_kanwil}: mengambil post {index}/{len(post_links)}",
                    "account": account.nama_kanwil,
                })

            shortcode = extract_shortcode(post_url)
            media_type = detect_media_type(post_url)

            tanggal = None
            caption = ""
            like_count = None
            comment_count = None
            total_engagement = None
            periode_status = "Tanggal Tidak Dicek"
            detail_status = "Link Only"
            catatan = ""

            if with_detail:
                detail = get_post_detail(context, post_url, period_start, period_end)
                tanggal = detail["tanggal_postingan"]
                caption = detail["caption"]
                like_count = detail["like_count"]
                comment_count = detail["comment_count"]
                total_engagement = detail["total_engagement"]
                periode_status = detail["status_periode"]
                detail_status = detail["status_scraping"]
                catatan = detail["catatan"]

            rows.append(
                ScrapeRow(
                    nama_kanwil=account.nama_kanwil,
                    url_akun=account.url_akun,
                    post_url=post_url,
                    shortcode=shortcode,
                    tanggal_postingan=tanggal,
                    media_type=media_type,
                    caption=caption,
                    like_count=like_count,
                    comment_count=comment_count,
                    total_engagement=total_engagement,
                    status_periode=periode_status,
                    status_scraping=detail_status,
                    catatan=catatan,
                )
            )

    except PlaywrightTimeoutError as exc:
        rows.append(
            build_empty_row(
                account,
                "Timeout",
                str(exc)[:300],
            )
        )

    except Exception as exc:
        rows.append(
            build_empty_row(
                account,
                "Failed",
                str(exc)[:300],
            )
        )

    finally:
        page.close()

    return rows


def should_stop_rows(rows: List[ScrapeRow], stop_on_login: bool) -> bool:
    if not stop_on_login:
        return False

    return any(row.status_scraping == "Login Wall" for row in rows)


def is_failed_account(rows: List[ScrapeRow]) -> bool:
    if not rows:
        return True

    if any(row.post_url for row in rows):
        return False

    failed_statuses = {
        "Login Wall",
        "Tidak Ada Link Terbaca",
        "Timeout",
        "Failed",
        "Blocked",
    }

    return any(row.status_scraping in failed_statuses for row in rows)


def run_scraping(
    accounts: List[AccountRow],
    period_start: datetime,
    period_end: datetime,
    max_posts: int,
    scrolls: int,
    delay: float,
    with_detail: bool,
    show_browser: bool,
    progress: Optional[Callable] = None,
    stop_on_login: bool = True,
    stop_after_failed_streak: bool = True,
    failed_streak_limit: int = 3,
) -> List[ScrapeRow]:
    all_rows = []
    total_accounts = len(accounts)
    failed_streak = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show_browser)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        for index, account in enumerate(accounts, start=1):
            if progress:
                progress({
                    "stage": "scrape",
                    "index": index,
                    "total": total_accounts,
                    "message": f"Memproses {index}/{total_accounts} - {account.nama_kanwil}",
                    "account": account.nama_kanwil,
                })

            rows = scrape_profile(
                context=context,
                account=account,
                max_posts=max_posts,
                scrolls=scrolls,
                with_detail=with_detail,
                period_start=period_start,
                period_end=period_end,
                total_accounts=total_accounts,
                progress=progress,
            )

            all_rows.extend(rows)

            if should_stop_rows(rows, stop_on_login):
                if progress:
                    progress({
                        "stage": "stop",
                        "index": index,
                        "total": total_accounts,
                        "message": f"Proses dihentikan. Instagram meminta login pada {account.nama_kanwil}.",
                        "account": account.nama_kanwil,
                    })
                break

            if is_failed_account(rows):
                failed_streak += 1
            else:
                failed_streak = 0

            if stop_after_failed_streak and failed_streak >= failed_streak_limit:
                if progress:
                    progress({
                        "stage": "stop",
                        "index": index,
                        "total": total_accounts,
                        "message": f"Proses dihentikan karena {failed_streak_limit} akun berturut-turut gagal terbaca.",
                        "account": account.nama_kanwil,
                    })
                break

            if index < total_accounts and context.pages:
                context.pages[0].wait_for_timeout(int(delay * 1000))

        context.close()
        browser.close()

    return all_rows