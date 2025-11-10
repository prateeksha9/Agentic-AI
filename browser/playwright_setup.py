# browser/playwright_setup.py
import json, os
from playwright.async_api import async_playwright

COOKIES_DIR = os.path.expanduser("~/.softlight/cookies")

async def get_browser_context(app_name: str):
    """Return a Playwright browser context that reuses saved cookies."""
    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookie_path = os.path.join(COOKIES_DIR, f"{app_name}_cookies.json")

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context()

    # Load cookies if file exists
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print(f"🔹 Loaded saved cookies for {app_name}")
        except Exception as e:
            print(f"⚠️ Couldn't load cookies: {e}")

    page = await context.new_page()
    return p, browser, context, page, cookie_path


async def save_cookies(context, cookie_path: str):
    """Save cookies to disk for next session."""
    cookies = await context.cookies()
    with open(cookie_path, "w") as f:
        json.dump(cookies, f)
    print(f"Cookies saved to {cookie_path}")
