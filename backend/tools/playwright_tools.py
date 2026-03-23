import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def fetch_application_form(url: str) -> dict:
    """
    Launch a headless browser, navigate to the application URL, and scrape visible form fields.
    Returns {"fields": [...], "title": "...", "url": url} or {"status": "manual_required", "url": url} on failure.
    """
    try:
        with sync_playwright() as p:
            with p.chromium.launch(headless=True) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=15000)
                inputs = page.query_selector_all("input, textarea, select")
                fields = []
                for el in inputs:
                    input_type = el.get_attribute("type") or "text"
                    if input_type in ("file", "hidden", "submit", "button"):
                        continue
                    if not el.is_visible():
                        continue
                    fields.append({
                        "name": el.get_attribute("name") or el.get_attribute("id") or "",
                        "type": input_type,
                        "id": el.get_attribute("id") or "",
                        "placeholder": el.get_attribute("placeholder") or "",
                    })
                if not fields:
                    logger.warning(f"No fillable fields found on {url} — may require authentication or JS rendering")
                    return {"status": "manual_required", "url": url, "error": "No fillable fields found"}
                return {"fields": fields, "title": page.title(), "url": url}
    except Exception as e:
        logger.warning(f"Form scraping failed for {url}: {e}")
        return {"status": "manual_required", "url": url, "error": str(e)}


def open_prefilled_form(url: str, payload: dict) -> None:
    """
    Open a real (non-headless) browser window with form fields pre-filled.
    Returns immediately — the browser stays open for the user to review and submit manually.
    The user confirms submission via the frontend "Mark as Submitted" button,
    which calls PATCH /applications/{id} with status=submitted.
    """
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=15000)
        for field_name, value in payload.items():
            try:
                input_type_check = page.locator(f"input[name='{field_name}'], select[name='{field_name}'], input[id='{field_name}'], select[id='{field_name}']").first
                tag_name = input_type_check.evaluate("el => el.tagName.toLowerCase()", timeout=1000)
                if tag_name == "select":
                    input_type_check.select_option(str(value))
                else:
                    locator = page.locator(f"[name='{field_name}'], [id='{field_name}']").first
                    locator.fill(str(value))
            except Exception as e:
                logger.debug(f"Could not fill field {field_name}: {e}")
        # Browser is intentionally left open for the user to review and submit manually.
        # Do not call browser.close() here.
    except Exception as e:
        logger.warning(f"Failed to open pre-filled browser for {url}: {e}")
