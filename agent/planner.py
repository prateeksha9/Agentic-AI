import os, yaml, re
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─────────────────────────────────────────────
# YAML Cleaning Utilities
# ─────────────────────────────────────────────
def clean_yaml_block(text: str) -> str:
    """Robust cleaner for Markdown code fences (```yaml ... ```)."""
    text = text.strip()
    text = re.sub(r"(?s)^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def normalize_plan_dict(plan_dict):
    """Ensure consistent list-of-dicts structure."""
    if isinstance(plan_dict, dict):
        plan_dict = [plan_dict]
    return plan_dict


def safe_str(x):
    return str(x).strip() if x is not None else ""


# ─────────────────────────────────────────────
# Plan Generator (LLM + RAG)
# ─────────────────────────────────────────────
def generate_plan(task: str):
    retriever = SimpleRetriever()
    retrieved = retriever.retrieve(task)
    context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

    # Context-aware prompt for both SauceDemo and TodoMVC
    prompt = f"""
You are Agent B, a precise automation planner.
Convert the user's natural language task into a YAML DSL plan.

Available actions:
  - open → open a URL
  - fill → type text into an input field (selector + value)
  - press → press a keyboard key (e.g., ENTER)
  - find_and_click → click a button or link
  - expect → verify a selector or text is visible
  - mark_completed → mark a todo as completed
  - delete_todo → delete a todo item
  - clear_completed → clear completed todos
  - wait_for → wait briefly or for a selector

Task: {task}
Context from knowledge base:
{context}

 SauceDemo Rules:
- URL: https://www.saucedemo.com/
- For login always use:
    fill → #user-name  value: standard_user
    fill → #password   value: secret_sauce
    find_and_click → #login-button
    expect → .inventory_list
- Only include add/remove cart steps if explicitly asked.
- Cart icon selector: a.shopping_cart_link
- Product add button: button.btn_inventory:has-text('Add to cart')
- Cart item selector: .cart_item

 TodoMVC Rules:
- URL: https://demo.playwright.dev/todomvc
- To add tasks:
    fill → input.new-todo
    press → ENTER
- To mark tasks done:
    mark_completed → <task name>
- To clear done tasks:
    clear_completed → 
- Never use visible text like “What needs to be done?” as a selector.

Return ONLY valid YAML (no markdown fences).
Each step must include 'action' and 'target', and 'value' when needed.
"""

    # Generate with GPT-4o-mini
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = clean_yaml_block(response.choices[0].message.content.strip())

    # Parse safely
    try:
        plan_dict = yaml.safe_load(plan_yaml)
    except yaml.YAMLError:
        print("\n⚠️ YAML parse failed — retrying after cleaning again...\n")
        plan_yaml = clean_yaml_block(plan_yaml)
        plan_dict = yaml.safe_load(plan_yaml)

    plan_dict = normalize_plan_dict(plan_dict)

    # ─────────────────────────────────────────────
    # Smart corrections (app-specific)
    # ─────────────────────────────────────────────
    fixed = []
    task_l = task.lower()

    for step in plan_dict:
        a = safe_str(step.get("action")).lower()
        t = safe_str(step.get("target"))
        v = safe_str(step.get("value"))

        # ---------- SAUCE DEMO ----------
        # if "sauce" in task_l:
        #     # Case 1: Login only
        #     if "login" in task_l and not any(k in task_l for k in ["add", "cart", "open"]):
        #         fixed = [
        #             {"action": "open", "target": "https://www.saucedemo.com/"},
        #             {"action": "fill", "target": "#user-name", "value": "standard_user"},
        #             {"action": "fill", "target": "#password", "value": "secret_sauce"},
        #             {"action": "find_and_click", "target": "#login-button"},
        #             {"action": "expect", "target": ".inventory_list"},
        #         ]
        #         break

        #     # Case 2: Add to cart only
        #     elif all(k in task_l for k in ["add", "open", "cart", "remove"]):
        #         fixed = [
        #             {"action": "open", "target": "https://www.saucedemo.com/"},
        #             {"action": "fill", "target": "#user-name", "value": "standard_user"},
        #             {"action": "fill", "target": "#password", "value": "secret_sauce"},
        #             {"action": "find_and_click", "target": "#login-button"},
        #             {"action": "find_and_click", "target": "button.btn_inventory:has-text('Add to cart')"},
        #             {"action": "find_and_click", "target": "a.shopping_cart_link"},
        #             {"action": "find_and_click", "target": "button:has-text('Remove')"},
        #             {"action": "expect", "target": "text=Continue Shopping"},
        #         ]
        #         break


        #     # Case 3: Add to cart and open cart page
        #     elif "add" in task_l and "open" in task_l and "cart" in task_l:
        #         fixed = [
        #             {"action": "open", "target": "https://www.saucedemo.com/"},
        #             {"action": "fill", "target": "#user-name", "value": "standard_user"},
        #             {"action": "fill", "target": "#password", "value": "secret_sauce"},
        #             {"action": "find_and_click", "target": "#login-button"},
        #             {"action": "find_and_click", "target": "button.btn_inventory:has-text('Add to cart')"},
        #             {"action": "find_and_click", "target": "a.shopping_cart_link"},
        #             {"action": "expect", "target": ".cart_item"},
        #         ]
        #         break

        #     # Case 4: Open side menu and capture options (non-URL UI state)
        #     elif "open" in task_l and "menu" in task_l and "sauce" in task_l:
        #         fixed = [
        #             {"action": "open", "target": "https://www.saucedemo.com/"},
        #             {"action": "fill", "target": "#user-name", "value": "standard_user"},
        #             {"action": "fill", "target": "#password", "value": "secret_sauce"},
        #             {"action": "find_and_click", "target": "#login-button"},
        #             {"action": "find_and_click", "target": "#react-burger-menu-btn"},
        #             {"action": "expect", "target": ".bm-menu"},
        #         ]
        #         break


        if "sauce" in task_l:
            # Case 1: Login only
            if "login" in task_l and not any(k in task_l for k in ["add", "cart", "open"]):
                fixed = [
                    {"action": "open", "target": "https://www.saucedemo.com/"},
                    {"action": "fill", "target": "#user-name", "value": "standard_user"},
                    {"action": "fill", "target": "#password", "value": "secret_sauce"},
                    {"action": "find_and_click", "target": "#login-button"},
                    {"action": "expect", "target": ".inventory_list"},
                ]
                break

            # 🆕 Case 2A: Add to cart only (no “open cart” mentioned)
            elif "add" in task_l and "cart" in task_l and "remove" not in task_l and "open" not in task_l:
                fixed = [
                    {"action": "open", "target": "https://www.saucedemo.com/"},
                    {"action": "fill", "target": "#user-name", "value": "standard_user"},
                    {"action": "fill", "target": "#password", "value": "secret_sauce"},
                    {"action": "find_and_click", "target": "#login-button"},
                    {"action": "expect", "target": ".inventory_list"},
                    {"action": "find_and_click", "target": "button.btn_inventory:has-text('Add to cart')"},
                    {"action": "expect", "target": "button.btn_inventory:has-text('Remove')"},
                ]
                break

            # Case 3: Add to cart and open cart page
            elif "add" in task_l and "open" in task_l and "cart" in task_l and "remove" not in task_l:
                fixed = [
                    {"action": "open", "target": "https://www.saucedemo.com/"},
                    {"action": "fill", "target": "#user-name", "value": "standard_user"},
                    {"action": "fill", "target": "#password", "value": "secret_sauce"},
                    {"action": "find_and_click", "target": "#login-button"},
                    {"action": "expect", "target": ".inventory_list"},
                    {"action": "find_and_click", "target": "button.btn_inventory:has-text('Add to cart')"},
                    {"action": "find_and_click", "target": "a.shopping_cart_link"},
                    {"action": "expect", "target": ".cart_item"},
                ]
                break

            # Case 4: Add to cart, open cart, and remove item
            elif all(k in task_l for k in ["add", "open", "cart", "remove"]):
                fixed = [
                    {"action": "open", "target": "https://www.saucedemo.com/"},
                    {"action": "fill", "target": "#user-name", "value": "standard_user"},
                    {"action": "fill", "target": "#password", "value": "secret_sauce"},
                    {"action": "find_and_click", "target": "#login-button"},
                    {"action": "expect", "target": ".inventory_list"},
                    {"action": "find_and_click", "target": "button.btn_inventory:has-text('Add to cart')"},
                    {"action": "find_and_click", "target": "a.shopping_cart_link"},
                    {"action": "find_and_click", "target": "button.cart_button:has-text('Remove')"},
                    {"action": "expect", "target": "text=Continue Shopping"},
                ]
                break

            # Case 5: Open side menu and capture options (non-URL UI state)
            elif "open" in task_l and "menu" in task_l and "sauce" in task_l:
                fixed = [
                    {"action": "open", "target": "https://www.saucedemo.com/"},
                    {"action": "fill", "target": "#user-name", "value": "standard_user"},
                    {"action": "fill", "target": "#password", "value": "secret_sauce"},
                    {"action": "find_and_click", "target": "#login-button"},
                    {"action": "find_and_click", "target": "#react-burger-menu-btn"},
                    {"action": "expect", "target": ".bm-menu"},
                ]
                break



        # ---------- TODO MVC ----------
        elif "todo" in task_l:

            # Case: Filter to show only completed todos
            if "filter" in task_l and "completed" in task_l:
                fixed = [
                    {"action": "open", "target": "https://demo.playwright.dev/todomvc"},
                    {"action": "wait_for", "target": "footer", "value": ""},
                    {"action": "find_and_click", "target": "a[href='#/completed']"},
                    {"action": "wait_for", "target": "ul.todo-list li.completed", "value": ""},
                    {"action": "expect", "target": "ul.todo-list li.completed", "value": ""},
                ]
                break

            # Case: Filter to show only active todos (optional)
            elif "filter" in task_l and "active" in task_l:
                fixed = [
                    {"action": "open", "target": "https://demo.playwright.dev/todomvc"},
                    {"action": "wait_for", "target": "footer", "value": ""},
                    {"action": "find_and_click", "target": "a[href='#/active']"},
                    {"action": "wait_for", "target": "ul.todo-list li:not(.completed)", "value": ""},
                    {"action": "expect", "target": "ul.todo-list li:not(.completed)", "value": ""},
                ]
                break

            # Generic fallback for TodoMVC
            if a == "fill" and not t:
                t = "input.new-todo"
            elif a == "expect" and not t and v:
                t = f"li:has-text('{v}')"
            fixed.append({"action": a, "target": t, "value": v})

        else:
            fixed.append({"action": a, "target": t, "value": v})

    if not fixed:
        fixed = plan_dict

    print("[blue] Plan sanitized for app context[/blue]")
    return load_dsl_from_dict(fixed)


# ─────────────────────────────────────────────
# Plan Repairer
# ─────────────────────────────────────────────
def repair_plan(failed_step, error_message, current_plan):
    """Ask the LLM to repair or regenerate the plan after a failure."""
    prompt = f"""
You are a YAML DSL repair agent for a Playwright-based automation system.

Valid actions:
  - open
  - find_and_click
  - fill
  - press
  - expect
  - wait_for

One step in the plan failed.

Failed step:
{failed_step}

Error:
{error_message}

Current plan:
{yaml.dump([s.__dict__ for s in current_plan])}

Return ONLY the corrected YAML (no markdown fences, no prose).
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = clean_yaml_block(response.choices[0].message.content.strip())
    try:
        plan_dict = yaml.safe_load(plan_yaml)
        if not plan_dict:
            print("[red]⚠️ LLM returned empty YAML — skipping repair.[/red]")
            return None
        plan_dict = normalize_plan_dict(plan_dict)
        return load_dsl_from_dict(plan_dict)
    except Exception as e:
        print(f"[red]Failed to parse repaired plan: {e}[/red]")
        print(f"[yellow]Raw YAML from LLM:[/yellow]\n{plan_yaml}\n")
        return None
