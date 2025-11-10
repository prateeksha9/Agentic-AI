# agent/executor.py
import asyncio
from rich import print
from browser.playwright_setup import get_browser_context, save_cookies
from pathlib import Path
from agent.capture import capture_state
from utils.dataset_summary import generate_summary
from agent.planner import repair_plan
import os

async def execute_plan(plan, app_name="todomvc", repair_attempts=0, max_repairs=3):
    """Execute DSL plan in browser with self-repair and stable UI handling."""
    async_playwright, browser, context, page, cookie_path = await get_browser_context(app_name)

    from datetime import datetime

    # Create a single consistent run folder for this session
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

            # OPEN
            if action == "open":
                await page.goto(target, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                print(f"[green]Opened {target}[/green]")
                await capture_state(page, step_index + 1, "open", app_name, base_dir)

            elif action == "find_and_click":
                target_norm = target.lower().replace("'", "").replace('"', "")
                locator = None

                # Try CSS with :has-text
                if "add to cart" in target_norm:
                    locator = page.locator('button:has-text("Add to cart")')
                elif "remove" in target_norm:
                    locator = page.locator('button:has-text("Remove")')
                elif "cart" in target_norm:
                    locator = page.locator("a.shopping_cart_link")

                if locator and await locator.count():
                    await locator.first.scroll_into_view_if_needed()
                    await locator.first.click(timeout=10000)
                    print(f"[green]Clicked {target}[/green]")
                    await page.wait_for_timeout(800)
                    await capture_state(page, step_index + 1, f"click_{target}", app_name)
                else:
                    raise Exception(f"Could not locate element for target: {target}")


            # FILL
            # elif action == "fill":
            #     locator = page.locator(target)
            #     if not await locator.count():
            #         locator = page.get_by_placeholder(target)
            #     if not await locator.count():
            #         locator = page.get_by_label(target)
            #     if not await locator.count():
            #         locator = page.locator("input, textarea").first

            #     await locator.first.fill(value)
            #     await page.wait_for_timeout(500)
            #     print(f"[green]Filled {target} with '{value}'[/green]")
            #     await page.wait_for_timeout(600)
            #     await capture_state(page, step_index + 1, f"fill_{target}", app_name)


            elif action == "fill":
                # Normalize and sanitize target/value
                target = (target or "").strip().lower()
                value = (value or "").strip()

                # Skip empty values — no reason to fill nothing
                if not value:
                    print(f"[yellow]⚠️ No value provided to fill for: {target}[/yellow]")
                    step_index += 1
                    continue

                locator = None

                # 1️⃣ Try direct selector if it looks like a CSS or XPath
                try_selectors = []
                if target.startswith(("#", ".", "input", "textarea", "[", "css=", "//")):
                    try_selectors.append(target.replace("css=", "").strip())

                # 2️⃣ Add likely common input fields (generic fallback)
                try_selectors += [
                    f"input[placeholder*='{target}']",
                    f"input[aria-label*='{target}']",
                    f"input[name*='{target}']",
                    f"textarea[placeholder*='{target}']",
                    "input[type='text']",
                    "textarea",
                    "input"
                ]

                # 3️⃣ Deduplicate the list (to avoid retrying the same)
                try_selectors = list(dict.fromkeys(try_selectors))

                # 4️⃣ Attempt sequential fallback matching
                for sel in try_selectors:
                    locator = page.locator(sel)
                    try:
                        if await locator.count():
                            await locator.first.scroll_into_view_if_needed()
                            await locator.first.wait_for(state="visible", timeout=3000)
                            break
                    except Exception:
                        continue

                # 5️⃣ If not found, try Playwright’s semantic helpers (placeholder/label)
                if not locator or not await locator.count():
                    locator = page.get_by_placeholder(target)
                if not locator or not await locator.count():
                    locator = page.get_by_label(target)

                # 6️⃣ Fallback — just grab the first visible text input on page
                if not locator or not await locator.count():
                    locator = page.locator("input:not([type=hidden]), textarea").first

                # 7️⃣ Final validation before filling
                if not locator or not await locator.count():
                    raise Exception(f"Could not locate any fillable input for: {target}")

                # 8️⃣ Perform the fill operation safely
                try:
                    await locator.first.fill(value)
                    print(f"[green]Filled {target or '[detected input]'} with '{value}'[/green]")
                    await page.wait_for_timeout(600)
                    await capture_state(page, step_index + 1, f"fill_{target or 'input'}", app_name, base_dir)
                except Exception as fill_error:
                    raise Exception(f"Failed to fill {target}: {fill_error}")


            elif action == "login" or ("login" in target.lower()):
                print("[blue]Initiating smart login sequence...[/blue]")
                await page.goto("https://www.saucedemo.com/", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("#user-name", timeout=8000)
                await page.wait_for_selector("#password", timeout=8000)

                # Normalize selectors and ensure clean fields
                username_selector = "#user-name"
                password_selector = "#password"
                login_button_selector = "#login-button"

                # Clear if any previous value exists
                await page.fill(username_selector, "")
                await page.fill(password_selector, "")

                # Always fill lowercase standardized credentials
                await page.fill(username_selector, "standard_user")
                await page.fill(password_selector, "secret_sauce")

                # Explicit click and confirm redirect
                await page.click(login_button_selector)
                await page.wait_for_url("**/inventory.html", timeout=10000)

                print(f"[green]✅ Logged in successfully[/green]")
                await capture_state(page, step_index + 1, "login_success", app_name)
                await page.wait_for_timeout(1000)

            elif action == "press":
                target_norm = target.lower().strip()

                # 🟢 CASE 1: Pressing a key like Enter / Tab / Escape
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

                # 🟢 CASE 2: It's actually a button (like #login-button)
                elif "#login-button" in target_norm or "login" in target_norm:
                    await page.locator("#login-button").click()
                    print(f"[green]Clicked login button[/green]")

                # 🟢 CASE 3: Generic fallback — press Enter in first input
                else:
                    inputs = page.locator("input")
                    if await inputs.count() > 0:
                        await inputs.first.focus()
                        await page.keyboard.press("Enter")
                        print(f"[green]Pressed Enter in first input[/green]")
                    else:
                        raise Exception(f"Unknown press target: {target}")

                await page.wait_for_timeout(800)
                await capture_state(page, step_index + 1, f"press_{target_norm}", app_name)

            elif action == "expect":
                try:
                    import re
                    target_norm = target.strip().lower()

                    # Handle CSS selectors directly (e.g. .class, #id, a.class)
                    if target_norm.startswith((".", "#")) or re.match(r"^[a-z]+\.", target_norm):
                        await page.wait_for_selector(target_norm, timeout=8000, state="visible")
                        print(f"[green]✅ Verified element present (CSS): {target_norm}[/green]")

                    # Handle :has-text("...") pattern
                    elif "has-text" in target_norm:
                        m = re.search(r"has-text\(['\"](.+?)['\"]\)", target_norm)
                        if m:
                            text_value = m.group(1).strip()
                            possible_texts = [text_value, text_value.capitalize(), text_value.upper()]
                            found = False
                            for t in possible_texts:
                                try:
                                    await page.wait_for_selector(f'text="{t}"', timeout=8000, state="visible")
                                    print(f"[green]✅ Verified text present: {t}[/green]")
                                    found = True
                                    break
                                except:
                                    continue
                            if not found:
                                raise Exception(f"Element not found with text variations: {possible_texts}")
                        else:
                            raise ValueError("Could not extract text from has-text selector")


                    # 🟢 3️⃣ Fallback: plain visible text
                    else:
                        possible_selectors = [
                            f'text="{target_norm}"',
                            f'text="{target_norm.capitalize()}"'
                        ]
                        found = False
                        for sel in possible_selectors:
                            try:
                                await page.wait_for_selector(sel, timeout=8000, state="visible")
                                print(f"[green]✅ Verified visible text: {sel}[/green]")
                                found = True
                                break
                            except:
                                continue
                        if not found:
                            raise Exception(f"Element not found with text or selector: {target_norm}")

                except Exception as e:
                    print(f"[red]❌ Could not verify: {target} — {e}[/red]")

                await page.wait_for_timeout(600)
                await capture_state(page, step_index + 1, f"expect_{target_norm}", app_name)


            elif action == "wait_for":
                await page.wait_for_timeout(1000)
                print(f"[yellow]Waited briefly for: {target}[/yellow]")

            else:
                print(f"[yellow]Unknown action: {action}[/yellow]")

            step_index += 1  # move to next step

        # ============ REPAIR LOOP ============
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

                print("[cyan]Received corrected plan from LLM. Updating current plan and retrying failed step...[/cyan]")
                plan = new_plan
                repair_attempts += 1
                continue  # retry same step without relaunching
            except Exception as re:
                print(f"[red]Repair attempt failed: {re}[/red]")
                break

    print("[green]All steps executed (with self-correction if needed).[/green]")
    await browser.close()
    await async_playwright.stop()

    # base_dir = Path(f"dataset/{app_name}")
    # latest_run = sorted(base_dir.glob("run_*"))[-1]
    # generate_summary(latest_run)

    generate_summary(base_dir)
    print(f"[green]✅ Dataset summary generated at: {base_dir}/dataset_summary.csv[/green]")




def run_executor(plan, app_name="todomvc"):
    """Sync wrapper for async Playwright execution."""
    asyncio.run(execute_plan(plan, app_name))
