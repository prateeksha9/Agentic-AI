# agent/executor.py
import asyncio
import os
import re
from rich import print
from pathlib import Path
from datetime import datetime

from browser.playwright_setup import get_browser_context, save_cookies_and_state
from agent.capture import capture_state
from utils.dataset_summary import generate_summary
from agent.planner import repair_plan
from dsl.parser import load_dsl_from_dict


# Disable HuggingFace fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


async def execute_plan(
    plan,
    app_name="todomvc",
    task_description=None,
    repair_attempts=0,
    max_repairs=3,
):
    """Execute DSL plan in browser with robust error handling and dataset capture."""

    async_playwright, browser, context, page, cookie_path = await get_browser_context(app_name)

    # 🧱 Base dataset directory
    base_app_dir = Path(f"dataset/{app_name}")
    base_app_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_name(text: str):
        import re
        text = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").lower()).strip("_")
        return text[:60] if text else "run"

    label = sanitize_name(task_description or getattr(plan, "task_description", "run"))
    existing_runs = [p for p in base_app_dir.glob("run_*") if p.is_dir()]
    next_index = len(existing_runs) + 1
    base_dir = base_app_dir / f"run_{next_index:02d}_{label}"
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"[blue]📁 Starting dataset capture: {base_dir}[/blue]")

    # =============================
    # Execute each DSL step
    # =============================
    step_index = 0
    while step_index < len(plan):
        step = plan[step_index]
        action = (step.action or "").strip().lower()
        target = (step.target or "").strip()
        value = (step.value or "").strip()
        print(f"[cyan]{step_index + 1}. Executing:[/cyan] {action} → {target or ''} {value or ''}")

        try:
            # ---------- OPEN ----------
            if action == "open":
                try:
                    await page.goto(target, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(1500)
                    print(f"[green]Opened {target}[/green]")
                except Exception as e:
                    print(f"[red]⚠️ Failed to open {target}: {e}[/red]")
                await capture_state(page, step_index + 1, "open", app_name, base_dir)

            # ---------- FIND AND CLICK ----------
            elif action == "find_and_click":
                locator = page.get_by_text(target)
                if not await locator.count():
                    locator = page.locator(f"text={target}")
                if not await locator.count():
                    print(f"[yellow]⚠️ Element not found for '{target}'. Skipping.[/yellow]")
                else:
                    try:
                        await locator.first.scroll_into_view_if_needed()
                        await locator.first.click(timeout=5000)
                        print(f"[green]Clicked '{target}'[/green]")
                    except Exception as e:
                        print(f"[red]⚠️ Click failed for '{target}': {e}[/red]")
                await capture_state(page, step_index + 1, f"click_{target}", app_name, base_dir)

            # ---------- FILL ----------
            elif action == "fill":
                try:
                    locator = page.locator("input.new-todo, input, textarea").first
                    if await locator.count():
                        await locator.fill(value)
                        print(f"[green]Filled '{target}' with '{value}'[/green]")
                    else:
                        print(f"[yellow]⚠️ No input field found for '{target}'[/yellow]")
                except Exception as e:
                    print(f"[red]⚠️ Fill failed: {e}[/red]")
                await capture_state(page, step_index + 1, f"fill_{target}", app_name, base_dir)

            # ---------- PRESS ----------
            elif action == "press":
                try:
                    key = target.capitalize() if target else "Enter"
                    await page.keyboard.press(key)
                    print(f"[green]Pressed {key}[/green]")
                except Exception as e:
                    print(f"[red]⚠️ Press failed: {e}[/red]")
                await capture_state(page, step_index + 1, f"press_{target}", app_name, base_dir)

            # ---------- EXPECT ----------
            elif action == "expect":
                try:
                    if await page.get_by_text(target).count():
                        print(f"[green]✅ Verified visible text: '{target}'[/green]")
                    else:
                        print(f"[yellow]❌ Expect failed — '{target}' not found[/yellow]")
                except Exception as e:
                    print(f"[red]⚠️ Expect lookup error for '{target}': {e}[/red]")
                await capture_state(page, step_index + 1, f"expect_{target}", app_name, base_dir)

            # ---------- WAIT ----------
            elif action == "wait_for":
                await page.wait_for_timeout(1000)
                print(f"[yellow]Waited briefly ({target or '1s'})[/yellow]")

            # ---------- MARK COMPLETED ----------
            elif action == "mark_completed" and app_name == "todomvc":
                try:
                    todo_item = page.locator(f"li:has(label:text-is('{target}'))").first
                    if await todo_item.count():
                        checkbox = todo_item.locator("input.toggle")
                        await checkbox.check()
                        print(f"[green]✅ Marked '{target}' as completed[/green]")
                    else:
                        print(f"[yellow]⚠️ Todo '{target}' not found to mark complete[/yellow]")
                except Exception as e:
                    print(f"[red]⚠️ mark_completed failed: {e}[/red]")
                await capture_state(page, step_index + 1, f"mark_{target}", app_name, base_dir)

            # ---------- DELETE TODO ----------
            elif action == "delete_todo" and app_name == "todomvc":
                try:
                    todo_item = page.locator(f"li:has(label:text-is('{target}'))").first
                    if await todo_item.count():
                        await todo_item.hover()
                        destroy_btn = todo_item.locator("button.destroy")
                        await destroy_btn.click()
                        print(f"[green]🗑️ Deleted todo '{target}'[/green]")
                    else:
                        print(f"[yellow]⚠️ Todo '{target}' not found to delete[/yellow]")
                except Exception as e:
                    print(f"[red]⚠️ delete_todo failed: {e}[/red]")
                await capture_state(page, step_index + 1, f"delete_{target}", app_name, base_dir)

            # ---------- CLEAR COMPLETED ----------
            # ---------- CLEAR COMPLETED ----------
            elif action == "clear_completed" and app_name == "todomvc":
                try:
                    button = page.get_by_text("Clear completed")
                    if await button.count():
                        await button.click()
                        print(f"[green]🧹 Cleared completed todos[/green]")
                    else:
                        print(f"[yellow]⚠️ 'Clear completed' button not found — deleting all todos manually[/yellow]")
                        todos = page.locator("ul.todo-list li")
                        count = await todos.count()
                        if count > 0:
                            for i in range(count):
                                item = todos.nth(0)
                                await item.hover()
                                destroy_btn = item.locator("button.destroy")
                                await destroy_btn.click()
                                await page.wait_for_timeout(300)
                            print(f"[green]🧹 Deleted {count} todos manually[/green]")
                        else:
                            print(f"[blue]ℹ️ No todos to delete[/blue]")
                except Exception as e:
                    print(f"[red]⚠️ clear_completed failed: {e}[/red]")
                await capture_state(page, step_index + 1, "clear_completed", app_name, base_dir)

            # elif action == "clear_completed" and app_name == "todomvc":
            #     try:
            #         button = page.get_by_text("Clear completed")
            #         if await button.count():
            #             await button.click()
            #             print(f"[green]🧹 Cleared completed todos[/green]")
            #         else:
            #             print(f"[yellow]⚠️ 'Clear completed' button not found[/yellow]")
            #     except Exception as e:
            #         print(f"[red]⚠️ clear_completed failed: {e}[/red]")
            #     await capture_state(page, step_index + 1, "clear_completed", app_name, base_dir)

            # ---------- UNKNOWN ----------
            else:
                print(f"[yellow]⚠️ Unknown action '{action}', skipping...[/yellow]")

            step_index += 1

        except Exception as e:
            print(f"[red]Step failed: {action} → {target} | {e}[/red]")
            await capture_state(page, step_index + 1, f"error_{action}", app_name, base_dir)
            if repair_attempts < max_repairs:
                print(f"[yellow]🔁 Attempting plan repair ({repair_attempts + 1}/{max_repairs})...[/yellow]")
                try:
                    new_plan = repair_plan(step, str(e), plan)
                    if new_plan and new_plan != plan:
                        plan = new_plan
                        repair_attempts += 1
                        print("[cyan]🔄 Retrying repaired plan...[/cyan]")
                        continue
                except Exception as re:
                    print(f"[red]Repair failed: {re}[/red]")
                    break
            else:
                print(f"[red]❌ Max repair attempts reached, aborting further repairs.[/red]")
                break

    print("[cyan]Execution complete — check logs for ⚠️ warnings or ❌ expectations.[/cyan]")
    await save_cookies_and_state(context, app_name, cookie_path)
    await browser.close()
    await async_playwright.stop()

    generate_summary(base_dir)
    print(f"[green]📊 Dataset summary generated at: {base_dir}/dataset_summary.csv[/green]")


def run_executor(plan_data, app_name="todomvc", task_description=None):
    """Helper to launch async executor from synchronous main.py."""
    plan = load_dsl_from_dict(plan_data)
    asyncio.run(execute_plan(plan, app_name, task_description))
