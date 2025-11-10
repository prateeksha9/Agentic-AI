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
                await capture_state(page, step_index + 1, "open", app_name)

            # FIND AND CLICK
            # elif action == "find_and_click":
            #     locator = page.get_by_role("button", name=target)
            #     if not await locator.count():
            #         locator = page.get_by_text(target)
            #     await locator.first.scroll_into_view_if_needed()
            #     await locator.first.wait_for(state="visible", timeout=8000)
            #     await locator.first.click()
            #     print(f"[green]Clicked {target}[/green]")
            #     await page.wait_for_timeout(600)
            #     await capture_state(page, step_index + 1, f"click_{target}", app_name)

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
            elif action == "fill":
                locator = page.locator(target)
                if not await locator.count():
                    locator = page.get_by_placeholder(target)
                if not await locator.count():
                    locator = page.get_by_label(target)
                if not await locator.count():
                    locator = page.locator("input, textarea").first

                await locator.first.fill(value)
                await page.wait_for_timeout(500)
                print(f"[green]Filled {target} with '{value}'[/green]")
                await page.wait_for_timeout(600)
                await capture_state(page, step_index + 1, f"fill_{target}", app_name)

            elif action == "login":
                await page.goto("https://www.saucedemo.com/")
                await page.fill("#user-name", "standard_user")
                await page.fill("#password", "secret_sauce")
                await page.click("#login-button")
                await page.wait_for_url("**/inventory.html")
                print(f"[green]Logged in successfully[/green]")
                await capture_state(page, step_index + 1, "login", app_name)


            # PRESS
            # elif action == "press":
            #     key = target.capitalize()

            #     # Focus an input field before pressing Enter
            #     try:
            #         input_field = await page.query_selector("input[placeholder], input, textarea")
            #         if input_field:
            #             await input_field.focus()
            #             print("[blue]Focused on input field before pressing key[/blue]")
            #         else:
            #             print("[yellow]No focusable input found, pressing key globally[/yellow]")
            #     except Exception as focus_error:
            #         print(f"[yellow]Warning: could not focus input: {focus_error}[/yellow]")

            #     try:
            #         if key in ["Enter", "Tab", "Escape", "Space"]:
            #             await page.keyboard.press(key)
            #         else:
            #             await page.keyboard.press("Enter")
            #     except Exception as press_error:
            #         raise Exception(f"Key press failed for '{key}': {press_error}")

            #     print(f"[green]Pressed {key}[/green]")
            #     await page.wait_for_timeout(800)
            #     await capture_state(page, step_index + 1, f"press_{key}", app_name)

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


            # EXPECT (real verification)
            # elif action == "expect":
            #     try:
            #         target_norm = target.lower().strip()
            #         import re
                    
            #         # 1️⃣ Extract text inside has-text() if present
            #         if "has-text" in target_norm:
            #             m = re.search(r"has-text\(['\"](.+?)['\"]\)", target_norm)
            #             if m:
            #                 text_value = m.group(1).strip()
            #             else:
            #                 text_value = target_norm
            #         else:
            #             text_value = target_norm

            #         # 2️⃣ Try common Playwright patterns — be forgiving about case
            #         possible_selectors = [
            #             f'button:has-text("{text_value}")',
            #             f'button:has-text("{text_value.capitalize()}")',
            #             f'text="{text_value}"',
            #             f'text="{text_value.capitalize()}"'
            #         ]

            #         found = False
            #         for sel in possible_selectors:
            #             try:
            #                 await page.wait_for_selector(sel, timeout=8000, state="visible")
            #                 print(f"[green]✅ Verified presence of element: {sel}[/green]")
            #                 found = True
            #                 break
            #             except:
            #                 continue

            #         if not found:
            #             raise Exception(f"Element not found with text '{text_value}' in any selector.")

            #     except Exception as e:
            #         print(f"[red]❌ Could not verify: {target} — {e}[/red]")

            #     await page.wait_for_timeout(600)
            #     await capture_state(page, step_index + 1, f"expect_{target}", app_name)

            elif action == "expect":
                try:
                    import re
                    target_norm = target.strip().lower()

                    # 🟢 1️⃣ Handle CSS selectors directly (e.g. .class, #id, a.class)
                    if target_norm.startswith((".", "#")) or re.match(r"^[a-z]+\.", target_norm):
                        await page.wait_for_selector(target_norm, timeout=8000, state="visible")
                        print(f"[green]✅ Verified element present (CSS): {target_norm}[/green]")

                    # 🟢 2️⃣ Handle :has-text("...") pattern
                    # elif "has-text" in target_norm:
                    #     m = re.search(r"has-text\(['\"](.+?)['\"]\)", target_norm)
                    #     if m:
                    #         text_value = m.group(1).strip()
                    #         await page.wait_for_selector(f'text="{text_value}"', timeout=8000, state="visible")
                    #         print(f"[green]✅ Verified text present: {text_value}[/green]")
                    #     else:
                    #         raise ValueError("Could not extract text from has-text selector")

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

    base_dir = Path(f"dataset/{app_name}")
    latest_run = sorted(base_dir.glob("run_*"))[-1]
    generate_summary(latest_run)


def run_executor(plan, app_name="todomvc"):
    """Sync wrapper for async Playwright execution."""
    asyncio.run(execute_plan(plan, app_name))
