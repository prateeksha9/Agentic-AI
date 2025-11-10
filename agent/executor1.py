# agent/executor.py
import asyncio
from rich import print
from browser.playwright_setup import get_browser_context, save_cookies

async def execute_plan(plan):
    async_playwright, browser, context, page, cookie_path = await get_browser_context("notion")

    for idx, step in enumerate(plan, start=1):
        action = step.action
        target = step.target
        value = step.value
        print(f"[cyan]{idx}. Executing:[/cyan] {action} → {target or ''} {value or ''}")

        try:
            if action == "open":
                await page.goto(target)
                await page.wait_for_load_state("networkidle")

                # Detect login requirement: look for "Sign in" or "Continue with email"
                if await page.get_by_text("Sign in").count() or await page.get_by_text("Continue with email").count():
                    print("[blue]🔐 Login required. Please complete login in the browser window.[/blue]")
                    input("Press Enter after you finish logging in...")
                    await save_cookies(context, cookie_path)

            elif action == "find_and_click":
                locator = page.get_by_role("button", name=target)
                if not await locator.count():
                    locator = page.get_by_text(target)
                await locator.first.scroll_into_view_if_needed()
                await locator.first.wait_for(state="visible", timeout=10000)
                await locator.first.click()

            elif action == "fill":
                locator = page.get_by_label(target)
                if not await locator.count():
                    locator = page.get_by_placeholder(target)
                await locator.first.fill(value)

            elif action == "press":
                await page.keyboard.press(target)

            elif action == "expect":
                print(f"✅ Expectation (placeholder): {target}")
                await page.wait_for_timeout(1000)

        except Exception as e:
            print(f"[red]❌ Error during {action}: {e}[/red]")

    print("[green]All steps executed![/green]")
    await browser.close()
    await async_playwright.stop()


def run_executor(plan):
    asyncio.run(execute_plan(plan))
