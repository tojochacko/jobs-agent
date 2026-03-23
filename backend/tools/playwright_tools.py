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
                    fields.append({
                        "name": el.get_attribute("name") or el.get_attribute("id") or "",
                        "type": input_type,
                        "id": el.get_attribute("id") or "",
                        "placeholder": el.get_attribute("placeholder") or "",
                    })
                return {"fields": fields, "title": page.title(), "url": url}
    except Exception as e:
        logger.warning(f"Form scraping failed for {url}: {e}")
        return {"status": "manual_required", "url": url, "error": str(e)}


def open_prefilled_form(url: str, payload: dict) -> None:
    """
    Open a real (non-headless) browser window with form fields pre-filled.
    Control is handed to the user; this function returns immediately after filling.
    The browser remains open for the user to submit manually.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=15000)
        for field_name, value in payload.items():
            try:
                locator = page.locator(f"[name='{field_name}'], [id='{field_name}']").first
                locator.fill(str(value))
            except Exception as e:
                logger.debug(f"Could not fill field {field_name}: {e}")
        # Leave browser open for user — do not close
        input("Press Enter in the terminal after you have submitted the form...")
        browser.close()
