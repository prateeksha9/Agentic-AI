# browser/playwright_setup.py
import json, os
from pathlib import Path
from playwright.async_api import async_playwright

# Use consistent storage directories under ~/.softlight
SOFTLIGHT_DIR = Path(os.path.expanduser("~/.softlight"))
COOKIES_DIR = SOFTLIGHT_DIR / "cookies"
STATE_DIR = SOFTLIGHT_DIR / "state"

COOKIES_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)


async def get_browser_context(app_name: str):
    """Return a Playwright browser context that reuses full session state (cookies + localStorage)."""
    cookie_path = COOKIES_DIR / f"{app_name}_cookies.json"
    state_path = STATE_DIR / f"state_{app_name}.json"

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)

    # ✅ Load previous state if available
    if state_path.exists():
        context = await browser.new_context(storage_state=str(state_path))
        print(f"[green]🔁 Loaded persisted state for {app_name}[/green]")
    else:
        context = await browser.new_context()
        print(f"[yellow]🆕 Created new browser context for {app_name}[/yellow]")

    # Also restore cookies (for backward compatibility)
    if cookie_path.exists():
        try:
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print(f"[blue]🍪 Loaded saved cookies for {app_name}[/blue]")
        except Exception as e:
            print(f"[red]⚠️ Couldn't load cookies: {e}[/red]")

    page = await context.new_page()
    return p, browser, context, page, str(cookie_path)


async def save_cookies_and_state(context, app_name: str, cookie_path: str):
    """Save both cookies and full storage state for persistence."""
    # Save cookies
    cookies = await context.cookies()
    with open(cookie_path, "w") as f:
        json.dump(cookies, f)
    print(f"[blue]💾 Cookies saved to {cookie_path}[/blue]")

    # Save Playwright state (localStorage + sessionStorage)
    state_path = STATE_DIR / f"state_{app_name}.json"
    await context.storage_state(path=str(state_path))
    print(f"[green]💾 State saved to {state_path}[/green]")
