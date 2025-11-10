# agent/executor.py
import asyncio
from rich import print
from browser.playwright_setup import get_browser_context, save_cookies
from pathlib import Path
from agent.capture import capture_state
from utils.dataset_summary import generate_summary
import os

async def execute_plan(plan, app_name="todomvc"):
    """Execute a DSL plan in the browser with screenshots and cookie handling."""
    async_playwright, browser, context, page, cookie_path = await get_browser_context(app_name)

    for idx, step in enumerate(plan, start=1):
        action = step.action
        target = step.target
        value = step.value
        print(f"[cyan]{idx}. Executing:[/cyan] {action} → {target or ''} {value or ''}")

        try:
            # ────────────────────────────────
            #  OPEN
            # ────────────────────────────────
            if action == "open":
                try:
                    await page.goto(target, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(2000)  # let SPA render
                    print(f"[green]✅ Opened {target}[/green]")
                except Exception as e:
                    print(f"[yellow]⚠️ Timeout or partial load: {e}[/yellow]")

                # If login UI detected (for future)
                if await page.get_by_text("Sign in").count():
                    print("[blue]🔐 Login page detected. Log in manually, then press Enter.[/blue]")
                    input("Press Enter after login is complete...")
                    await save_cookies(context, cookie_path)

                await capture_state(page, idx, "open", app_name)

            # ────────────────────────────────
            #  FIND & CLICK
            # ────────────────────────────────
            elif action == "find_and_click":
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(1000)
                locator = page.get_by_role("button", name=target)
                if not await locator.count():
                    locator = page.get_by_text(target)
                await locator.first.scroll_into_view_if_needed()
                await locator.first.wait_for(state="visible", timeout=10000)
                await locator.first.click()
                print(f"[green]✅ Clicked {target}[/green]")
                await page.wait_for_timeout(800)
                await capture_state(page, idx, f"click_{target}", app_name)

            # ────────────────────────────────
            #  FILL
            # ────────────────────────────────
            elif action == "fill":
                locator = page.get_by_placeholder(target)
                if not await locator.count():
                    locator = page.get_by_label(target)
                await locator.first.fill(value)
                print(f"[green]✅ Filled {target} with '{value}'[/green]")
                await page.wait_for_timeout(500)
                await capture_state(page, idx, f"fill_{target}", app_name)

            # ────────────────────────────────
            #  PRESS / KEYBOARD INPUT
            # ────────────────────────────────
            elif action == "press":
                await page.keyboard.press(target)
                print(f"[green]✅ Pressed {target}[/green]")
                await page.wait_for_timeout(800)
                await capture_state(page, idx, f"press_{target}", app_name)

            # ────────────────────────────────
            #  EXPECT (assert / check)
            # ────────────────────────────────
            elif action == "expect":
                await page.wait_for_timeout(1000)
                print(f"✅ Expectation (placeholder): {target}")
                await capture_state(page, idx, f"expect_{target}", app_name)

            # ────────────────────────────────
            #  UNKNOWN ACTION
            # ────────────────────────────────
            else:
                print(f"[yellow]⚠️ Unknown action: {action}[/yellow]")

        except Exception as e:
            print(f"[red]❌ Error during {action}: {e}[/red]")

    print("[green]All steps executed![/green]")
    await browser.close()
    await async_playwright.stop()

# agent/executor1.py (replace the fill logic)
async def execute_step(page, step):
    action = step.action
    target = step.target
    value = step.value

    if action == "open":
        await page.goto(target)

    elif action == "fill":
        try:
            # Try using CSS selector directly
            await page.fill(target, value)
        except Exception:
            # Fallback: try placeholder, label, role, etc.
            try:
                await page.get_by_placeholder(target).fill(value)
            except Exception:
                await page.get_by_label(target).fill(value)

    elif action == "press":
        await page.keyboard.press(target)

    elif action == "expect":
        locator = page.locator(target)
        await locator.wait_for(state="visible")
        assert value in await locator.inner_text(), f"Expected '{value}' not found."

    else:
        print(f"⚠️ Unknown action: {action}")


def run_executor(plan, app_name="todomvc"):
    """Sync wrapper for async Playwright execution."""
    asyncio.run(execute_plan(plan, app_name))
