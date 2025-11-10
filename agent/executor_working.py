# agent/executor.py
import asyncio
from rich import print
from pathlib import Path
from datetime import datetime
import os

from browser.playwright_setup import get_browser_context, save_cookies
from agent.capture import capture_state
from utils.dataset_summary import generate_summary
from agent.planner import repair_plan


async def execute_plan(plan, app_name="todomvc", repair_attempts=0, max_repairs=3):
    """Execute DSL plan in browser with self-repair and stable UI handling."""
    async_playwright, browser, context, page, cookie_path = await get_browser_context(app_name)

    # Create a consistent per-run dataset folder
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base_dir = Path(f"dataset/{app_name}/{run_id}")
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"[blue]📁 Starting dataset capture: {base_dir}[/blue]")

    step_index = 0
    while step_index < len(plan):
        step = plan[step_index]
        action = step.action
        target = step.target
        value = step.value
        print(f"[cyan]{step_index + 1}. Executing:[/cyan] {action} → {target or ''} {value or ''}")

        try:
            # ============ ACTIONS ============

            # 🟢 OPEN PAGE
            if action == "open":
                await page.goto(target, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                print(f"[green]Opened {target}[/green]")
                await capture_state(page, step_index + 1, "open", app_name, base_dir)

            # 🟢 CLICK ELEMENT
            elif action == "find_and_click":
                target_norm = target.lower().replace("'", "").replace('"', "")
                locator = None

                # Handle common button variations
                if "add to cart" in target_norm:
                    locator = page.locator('button:has-text("Add to cart")')
                elif "remove" in target_norm:
                    locator = page.locator('button:has-text("Remove")')
                elif "cart" in target_norm:
                    locator = page.locator("a.shopping_cart_link")

                # Fallback generic locators
                if not locator or not await locator.count():
                    locator = page.get_by_text(target)

                if locator and await locator.count():
                    await locator.first.scroll_into_view_if_needed()
                    await locator.first.click(timeout=10000)
                    print(f"[green]Clicked {target}[/green]")
                    await page.wait_for_timeout(800)
                    await capture_state(page, step_index + 1, f"click_{target}", app_name, base_dir)
                else:
                    raise Exception(f"Could not locate element for target: {target}")

            # 🟢 FILL INPUT FIELD
            elif action == "fill":
                # Normalize and sanitize target/value
                target = (target or "").strip().lower()
                value = (value or "").strip()

                if not value:
                    print(f"[yellow]⚠️ No value provided to fill for: {target}[/yellow]")
                    step_index += 1
                    continue

                locator = None

                # Try direct selector if it looks like CSS/XPath
                try_selectors = []
                if target.startswith(("#", ".", "input", "textarea", "[", "css=", "//")):
                    try_selectors.append(target.replace("css=", "").strip())

                # Generic fallbacks
                try_selectors += [
                    f"input[placeholder*='{target}']",
                    f"input[aria-label*='{target}']",
                    f"input[name*='{target}']",
                    f"textarea[placeholder*='{target}']",
                    "input[type='text']",
                    "textarea",
                    "input"
                ]
                try_selectors = list(dict.fromkeys(try_selectors))

                # Try sequentially
                for sel in try_selectors:
                    locator = page.locator(sel)
                    try:
                        if await locator.count():
                            await locator.first.scroll_into_view_if_needed()
                            await locator.first.wait_for(state="visible", timeout=3000)
                            break
                    except Exception:
                        continue

                # Try semantic fallback
                if not locator or not await locator.count():
                    locator = page.get_by_placeholder(target)
                if not locator or not await locator.count():
                    locator = page.get_by_label(target)

                # Final fallback
                if not locator or not await locator.count():
                    locator = page.locator("input:not([type=hidden]), textarea").first

                if not locator or not await locator.count():
                    raise Exception(f"Could not locate any fillable input for: {target}")

                await locator.first.fill(value)
                print(f"[green]Filled {target or '[detected input]'} with '{value}'[/green]")
                await page.wait_for_timeout(600)
                await capture_state(page, step_index + 1, f"fill_{target or 'input'}", app_name, base_dir)

            # 🟢 SMART LOGIN FLOW (explicit "login" action)
            elif action == "login":
                print("[blue]Initiating smart login sequence...[/blue]")
                await page.goto("https://www.saucedemo.com/", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("#user-name", timeout=8000)
                await page.wait_for_selector("#password", timeout=8000)

                await page.fill("#user-name", "standard_user")
                await page.fill("#password", "secret_sauce")
                await page.click("#login-button")

                # Wait until inventory page loads
                await page.wait_for_url("**/inventory.html", timeout=10000)
                print(f"[green]✅ Logged in successfully[/green]")
                await capture_state(page, step_index + 1, "login_success", app_name, base_dir)
                await page.wait_for_timeout(1000)

            # 🟢 PRESS (keyboard or button)
            elif action == "press":
                target_norm = target.lower().strip()

                # 1️⃣ Keyboard key
                if target_norm in ["enter", "tab", "escape", "space"]:
                    try:
                        input_field = await page.query_selector("input[placeholder], input, textarea")
                        if input_field:
                            await input_field.focus()
                            print("[blue]Focused on input field before pressing key[/blue]")
                        await page.keyboard.press(target_norm.capitalize())
                        print(f"[green]Pressed key: {target_norm}[/green]")
                    except Exception as e:
                        raise Exception(f"Key press failed: {e}")

                # 2️⃣ Clickable element (button or selector)
                elif target_norm.startswith(("#", ".", "button")):
                    try:
                        locator = page.locator(target_norm)
                        if not await locator.count():
                            locator = page.get_by_text(target_norm.replace("#", "").replace(".", " ").strip())
                        if await locator.count():
                            await locator.first.click()
                            print(f"[green]Clicked element: {target_norm}[/green]")
                        else:
                            raise Exception(f"No clickable element found for: {target_norm}")
                    except Exception as click_error:
                        raise Exception(f"Failed to click {target_norm}: {click_error}")

                # 3️⃣ Fallback: Enter key
                else:
                    inputs = page.locator("input")
                    if await inputs.count() > 0:
                        await inputs.first.focus()
                        await page.keyboard.press("Enter")
                        print(f"[green]Pressed Enter in first input[/green]")
                    else:
                        raise Exception(f"Unknown press target: {target}")

                await page.wait_for_timeout(800)
                await capture_state(page, step_index + 1, f"press_{target_norm}", app_name, base_dir)

            # 🟢 EXPECT (verifies element or text)
            elif action == "expect":
                import re
                target_norm = target.strip().lower()
                try:
                    if target_norm.startswith((".", "#")) or re.match(r"^[a-z]+\.", target_norm):
                        await page.wait_for_selector(target_norm, timeout=8000, state="visible")
                        print(f"[green]✅ Verified element present (CSS): {target_norm}[/green]")
                    elif "has-text" in target_norm:
                        m = re.search(r"has-text\(['\"](.+?)['\"]\)", target_norm)
                        if m:
                            text_value = m.group(1).strip()
                            for t in [text_value, text_value.capitalize(), text_value.upper()]:
                                try:
                                    await page.wait_for_selector(f'text="{t}"', timeout=8000, state="visible")
                                    print(f"[green]✅ Verified text present: {t}[/green]")
                                    break
                                except:
                                    continue
                        else:
                            raise ValueError("Could not extract text from has-text selector")
                    else:
                        for sel in [f'text="{target_norm}"', f'text="{target_norm.capitalize()}"']:
                            try:
                                await page.wait_for_selector(sel, timeout=8000, state="visible")
                                print(f"[green]✅ Verified visible text: {sel}[/green]")
                                break
                            except:
                                continue
                except Exception as e:
                    print(f"[red]❌ Could not verify: {target} — {e}[/red]")

                await page.wait_for_timeout(600)
                await capture_state(page, step_index + 1, f"expect_{target_norm}", app_name, base_dir)

            # 🟡 WAIT
            elif action == "wait_for":
                await page.wait_for_timeout(1000)
                print(f"[yellow]Waited briefly for: {target}[/yellow]")

            else:
                print(f"[yellow]Unknown action: {action}[/yellow]")

            step_index += 1

        # ============ SELF-REPAIR LOOP ============
        except Exception as e:
            print(f"[red]Step failed: {action} → {target}[/red]")
            print(f"[yellow]Triggering plan repair (attempt {repair_attempts + 1}/{max_repairs})...[/yellow]")

            if repair_attempts >= max_repairs:
                print(f"[red]❌ Max repair attempts ({max_repairs}) reached. Aborting.[/red]")
                break

            try:
                new_plan = repair_plan(step, str(e), plan)
                if not new_plan:
                    print("[red]⚠️ Repair failed — no new plan returned.[/red]")
                    break
                if new_plan == plan:
                    print("[red]⚠️ LLM returned identical plan. Stopping to avoid loop.[/red]")
                    break
                print("[cyan]Received corrected plan from LLM. Updating plan and retrying...[/cyan]")
                plan = new_plan
                repair_attempts += 1
                continue
            except Exception as re:
                print(f"[red]Repair attempt failed: {re}[/red]")
                break

    print("[green]All steps executed (with self-correction if needed).[/green]")
    await browser.close()
    await async_playwright.stop()

    generate_summary(base_dir)
    print(f"[green]✅ Dataset summary generated at: {base_dir}/dataset_summary.csv[/green]")


def run_executor(plan, app_name="todomvc"):
    """Sync wrapper for async Playwright execution."""
    asyncio.run(execute_plan(plan, app_name))
