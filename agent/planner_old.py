# agent/planner.py
import os, yaml
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

# def sanitize_plan(plan):
#     """Patch missing or wrong selectors in Sauce Demo or TodoMVC plans."""
#     fixed_plan = []
#     for step in plan:
#         a = (step.get("action") or "").lower()
#         t = (step.get("target") or "").strip()
#         v = (step.get("value") or "").strip()

#         # --- Sauce Demo login correction ---
#         if a == "fill" and ("user" in v.lower() or "secret" in v.lower()):
#             if "user" in v.lower():
#                 t = "#user-name"
#                 v = "standard_user"
#             elif "secret" in v.lower() or "pass" in v.lower():
#                 t = "#password"
#                 v = "secret_sauce"

#         # Default press target if missing
#         if a in ["press", "click"] and not t:
#             t = "#login-button"

#         # --- Normalize selectors ---
#         if "shopping_cart" in t.lower():
#             t = ".shopping_cart_link"
#         if "button:has-text" in t.lower():
#             import re
#             match = re.search(r'has-text\(["\']?([^"\')]+)', t, re.I)
#             if match:
#                 t = f'text={match.group(1).strip()}'

#         # --- Normalize known SauceDemo buttons ---
#         # if a in ["find_and_click", "expect"] and "text=add to cart" in t.lower():
#         #     t = "button#add-to-cart-sauce-labs-backpack"
#         # --- Fallback for SauceDemo if specific ID not found ---
#         # --- Fix case-insensitive Add to Cart buttons on SauceDemo ---
#         if a == "find_and_click":
#             if "add to cart" in t.lower():
#                 # Use case-insensitive visible button selector
#                 t = "button.btn_inventory:has-text('Add to cart')"
#             elif "add-to-cart" in t.lower():
#                 t = "button.btn_inventory:has-text('Add to cart')"

#         # --- Normalize 'Remove' buttons ---
#         elif a in ["find_and_click", "expect"] and "remove" in t.lower():
#             t = "button.btn_inventory:has-text('Remove')"


#         fixed_plan.append({"action": a, "target": t, "value": v})

#     # --- Ensure page fully loads after login ---
#     for i, step in enumerate(fixed_plan):
#         if step.get("target") == "#login-button":
#             fixed_plan.insert(i + 1, {"action": "wait_for", "target": ".inventory_list", "value": ""})
#             break

#     return fixed_plan

# def sanitize_plan(plan):
#     """Auto-fix selectors and normalize steps for SauceDemo & TodoMVC plans."""
#     fixed_plan = []

#     # Helper flags
#     app_context = ""
#     for step in plan:
#         a = (step.get("action") or "").lower()
#         t = (step.get("target") or "").strip()
#         v = (step.get("value") or "").strip()

#         # --- Determine app context ---
#         if "sauce" in t.lower() or "swag" in t.lower() or "login-button" in t.lower():
#             app_context = "sauce"
#         elif "todo" in t.lower() or "todomvc" in v.lower() or "input.new-todo" in t.lower():
#             app_context = "todo"

#         # --- 🔧 Common action normalization ---
#         if a in ["press", "click"] and not t:
#             # Default press target when missing
#             t = "#login-button" if app_context == "sauce" else "input.new-todo"

#         # --- SAUCE DEMO FIXES ---
#         if app_context == "sauce":
#             # Normalize login fields
#             if a == "fill" and ("user" in v.lower() or "secret" in v.lower()):
#                 if "user" in v.lower():
#                     t = "#user-name"
#                     v = "standard_user"
#                 elif "secret" in v.lower() or "pass" in v.lower():
#                     t = "#password"
#                     v = "secret_sauce"

#             # Wait after login before inventory actions
#             if t == "#login-button":
#                 fixed_plan.append({"action": a, "target": t, "value": v})
#                 fixed_plan.append({"action": "wait_for", "target": ".inventory_list", "value": ""})
#                 continue

#             # Normalize add-to-cart / remove buttons
#             if a == "find_and_click":
#                 if "add to cart" in t.lower() or "add-to-cart" in t.lower():
#                     t = "button.btn_inventory:has-text('Add to cart')"
#                 elif "remove" in t.lower():
#                     t = "button.btn_inventory:has-text('Remove')"

#             # Normalize shopping cart
#             if "shopping_cart" in t.lower():
#                 t = ".shopping_cart_link"

#             # Ensure add-to-cart waits
#             if "add-to-cart" in t or "btn_inventory" in t:
#                 fixed_plan.append({"action": "wait_for", "target": "button.btn_inventory", "value": ""})

#         # --- TODOMVC FIXES ---
#         elif app_context == "todo":
#             # Normalize todo input
#             if a == "fill" and "input" in t:
#                 t = "input.new-todo"

#             # Mark completed: click toggle next to label
#             # if a == "find_and_click" and "label" in t and "buy laptop" in t.lower():
#             #     t = 'ul.todo-list li:has(label:text("Buy laptop")) input.toggle'

#             # --- Mark completed (generic dynamic pattern) ---
#             if a == "find_and_click" and "label" in t and "todo-list" in t:
#                 import re
#                 match = re.search(r"has-text\(['\"]?([^'\")]+)['\"]?\)", t, re.I)
#                 if match:
#                     todo_text = match.group(1)
#                     t = f'ul.todo-list li:has(label:text("{todo_text}")) input.toggle'


#             # Delete or clear completed
#             if "clear-completed" in t:
#                 a = "find_and_click"
#                 t = "button.clear-completed"
#                 fixed_plan.append({"action": "wait_for", "target": "button.clear-completed", "value": ""})

#             # Generic waits for todos list
#             if "ul.todo-list" in t and a == "expect":
#                 fixed_plan.append({"action": "wait_for", "target": "ul.todo-list", "value": ""})

#         fixed_plan.append({"action": a, "target": t, "value": v})

#     # --- Final fallbacks ---
#     if app_context == "sauce":
#         # Ensure page fully loads post-login
#         if not any(s["target"] == ".inventory_list" for s in fixed_plan):
#             fixed_plan.insert(0, {"action": "wait_for", "target": ".inventory_list", "value": ""})
#     elif app_context == "todo":
#         # Ensure new-todo input always exists
#         if not any("input.new-todo" in s["target"] for s in fixed_plan):
#             fixed_plan.insert(0, {"action": "wait_for", "target": "input.new-todo", "value": ""})

#     return fixed_plan

# def sanitize_plan(plan):
#     """
#     Patch, normalize, and auto-heal YAML plans for known web apps
#     (SauceDemo + TodoMVC). Handles selector normalization, 
#     timing waits, and missing state conditions.
#     """
#     fixed_plan = []

#     # Detect app context based on URL or action pattern
#     app_context = "todo" if any("todo" in str(s).lower() for s in plan) else (
#         "sauce" if any("sauce" in str(s).lower() for s in plan) else "generic"
#     )

#     for step in plan:
#         a = (step.get("action") or "").lower()
#         t = (step.get("target") or "").strip()
#         v = (step.get("value") or "").strip()

#         # =====================================================================
#         # 🧩 SAUCE DEMO FIXES
#         # =====================================================================
#         if app_context == "sauce":
#             # Normalize credentials
#             if a == "fill" and ("user" in v.lower() or "secret" in v.lower()):
#                 if "user" in v.lower():
#                     t = "#user-name"
#                     v = "standard_user"
#                 elif "secret" in v.lower() or "pass" in v.lower():
#                     t = "#password"
#                     v = "secret_sauce"

#             # Default press → login button
#             if a in ["press", "click"] and not t:
#                 t = "#login-button"

#             # Fix selectors after login
#             if "shopping_cart" in t.lower():
#                 t = ".shopping_cart_link"
#             if "button:has-text" in t.lower():
#                 import re
#                 match = re.search(r'has-text\(["\']?([^"\')]+)', t, re.I)
#                 if match:
#                     t = f'text={match.group(1).strip()}'

#             # Fallback for generic Add to Cart buttons
#             if a == "find_and_click" and "add-to-cart" in t:
#                 t = "button.btn_inventory:has-text('Add to cart')"

#             # Normalize Remove button
#             elif a in ["find_and_click", "expect"] and "remove" in t.lower():
#                 t = "button.btn_inventory:has-text('Remove')"

#             # Ensure page is ready after login
#             if t == "#login-button":
#                 fixed_plan.append({"action": a, "target": t, "value": v})
#                 fixed_plan.append(
#                     {"action": "wait_for", "target": ".inventory_list", "value": ""}
#                 )
#                 continue

#         # =====================================================================
#         # 🧩 TODOMVC FIXES
#         # =====================================================================
#         elif app_context == "todo":
#             # Normalize todo input field
#             if a == "fill" and "input" in t:
#                 t = "input.new-todo"

#             # Handle marking a todo as completed
#             if a == "find_and_click" and "label" in t and "todo-list" in t:
#                 import re
#                 match = re.search(r"has-text\(['\"]?([^'\")]+)['\"]?\)", t, re.I)
#                 if match:
#                     todo_text = match.group(1)
#                     t = f'ul.todo-list li:has(label:text("{todo_text}")) input.toggle'
#                     # Wait for re-rendered completion state
#                     fixed_plan.append({
#                         "action": "wait_for",
#                         "target": f'ul.todo-list li:has(label:text("{todo_text}")) input.toggle',
#                         "value": ""
#                     })
#                     fixed_plan.append({
#                         "action": "wait_for",
#                         "target": f'ul.todo-list li.completed:has(label:text("{todo_text}"))',
#                         "value": ""
#                     })
#                     fixed_plan.append({
#                         "action": "expect",
#                         "target": f'ul.todo-list li.completed:has(label:text("{todo_text}"))',
#                         "value": ""
#                     })

#             # Handle "clear completed" buttons
#             if a in ["press", "find_and_click"] and "clear-completed" in t:
#                 a, t = "find_and_click", "button.clear-completed"
#                 # Wait until at least one completed todo exists
#                 fixed_plan.append({"action": "wait_for", "target": "ul.todo-list li.completed", "value": ""})
#                 fixed_plan.append({"action": "wait_for", "target": "button.clear-completed", "value": ""})
#                 # Retry click twice for React re-render
#                 fixed_plan.append({"action": "find_and_click", "target": "button.clear-completed", "value": ""})
#                 fixed_plan.append({"action": "wait_for", "target": "button.clear-completed", "value": ""})
#                 fixed_plan.append({"action": "find_and_click", "target": "button.clear-completed", "value": ""})

#             # Always ensure todo list is visible before expectations
#             if "ul.todo-list" in t and a == "expect":
#                 fixed_plan.append({"action": "wait_for", "target": "ul.todo-list", "value": ""})

#         # =====================================================================
#         # ✅ Common normalizations for all apps
#         # =====================================================================
#         if a in ["press", "click"] and not t:
#             t = "#login-button" if app_context == "sauce" else "input.new-todo"

#         # Append the step after adjustments
#         fixed_plan.append({"action": a, "target": t, "value": v})

#     # =====================================================================
#     # 🧩 Auto-heal for TodoMVC: ensure something is completed before clearing
#     # =====================================================================
#     if app_context == "todo":
#         needs_clear = any("clear-completed" in s.get("target", "") for s in fixed_plan)
#         has_toggle = any("input.toggle" in s.get("target", "") for s in fixed_plan)
#         if needs_clear and not has_toggle:
#             fixed_plan.insert(0, {
#                 "action": "find_and_click",
#                 "target": "ul.todo-list li:first-child input.toggle",
#                 "value": "",
#             })
#             fixed_plan.insert(1, {
#                 "action": "wait_for",
#                 "target": "ul.todo-list li.completed",
#                 "value": "",
#             })

#     return fixed_plan

# def sanitize_plan(plan):
#     """
#     Normalize and auto-correct plans for SauceDemo + TodoMVC.
#     Adds logic to properly mark todos as completed for 'mark all' tasks.
#     """
#     fixed_plan = []
#     plan_text = str(plan).lower()

#     # Detect context
#     app_context = (
#         "sauce" if "sauce" in plan_text or "swag" in plan_text else
#         "todo" if "todo" in plan_text or "todomvc" in plan_text else
#         "generic"
#     )

#     for step in plan:
#         a = (step.get("action") or "").lower()
#         t = (step.get("target") or "").strip()
#         v = (step.get("value") or "").strip()

#         # =================================================================
#         # 🧩 SAUCE DEMO
#         # =================================================================
#         if app_context == "sauce":
#             if a == "fill" and "user" in v.lower():
#                 t, v = "#user-name", "standard_user"
#             elif a == "fill" and ("pass" in v.lower() or "secret" in v.lower()):
#                 t, v = "#password", "secret_sauce"
#             elif a in ["press", "click"] and not t:
#                 t = "#login-button"
#             elif a == "find_and_click" and "add" in t.lower():
#                 t = "button.btn_inventory:has-text('Add to cart')"
#             elif "shopping_cart" in t:
#                 t = ".shopping_cart_link"
#             if t == "#login-button":
#                 fixed_plan.append({"action": a, "target": t, "value": v})
#                 fixed_plan.append({"action": "wait_for", "target": ".inventory_list", "value": ""})
#                 continue

#         # =================================================================
#         # 🧩 TODOMVC
#         # =================================================================
#         elif app_context == "todo":
#             # Normalize input
#             if a == "fill" and "input" in t:
#                 t = "input.new-todo"

#             # 🧠 If the task is 'mark all completed', insert toggles
#             if any(kw in plan_text for kw in ["mark all", "complete all", "finish all"]):
#                 fixed_plan = [
#                     {"action": "open", "target": "https://demo.playwright.dev/todomvc", "value": ""},
#                     {"action": "wait_for", "target": "ul.todo-list li label", "value": ""},
#                     {"action": "find_and_click", "target": "ul.todo-list li input.toggle", "value": ""},
#                     {"action": "wait_for", "target": "ul.todo-list li.completed", "value": ""},
#                     {"action": "expect", "target": "ul.todo-list li.completed", "value": ""},
#                 ]
#                 break  # override everything else

#             # 🧹 For clear_completed keep fallback behavior
#             if "clear-completed" in t or "clear" in t:
#                 t = "button.clear-completed"

#         fixed_plan.append({"action": a, "target": t, "value": v})

#     # Add input wait if TodoMVC
#     if app_context == "todo" and not any("input.new-todo" in s.get("target", "") for s in fixed_plan):
#         fixed_plan.insert(0, {"action": "wait_for", "target": "input.new-todo", "value": ""})

#     return fixed_plan


def sanitize_plan(plan):
    """
    Normalize and auto-correct plans for SauceDemo + TodoMVC.
    Adds robust handling for 'mark all completed' and 'complete all' tasks.
    """
    fixed_plan = []
    plan_text = str(plan).lower()

    # Detect which app we're in
    app_context = (
        "sauce" if "sauce" in plan_text or "swag" in plan_text else
        "todo" if "todo" in plan_text or "todomvc" in plan_text else
        "generic"
    )

    # =================================================================
    # 🧩 Special case: Mark all todos completed
    # =================================================================
    if app_context == "todo" and any(kw in plan_text for kw in ["mark all", "complete all", "finish all"]):
        print("[cyan]🔧 Overriding plan for 'mark all todos completed'[/cyan]")
        return [
            {"action": "open", "target": "https://demo.playwright.dev/todomvc", "value": ""},
            {"action": "wait_for", "target": "ul.todo-list li label", "value": ""},
            # Select *all* toggle checkboxes and click them one by one
            {"action": "find_and_click", "target": "input.toggle", "value": ""},
            {"action": "wait_for", "target": "ul.todo-list li.completed", "value": ""},
            {"action": "expect", "target": "ul.todo-list li.completed", "value": ""},
        ]

    # =================================================================
    # 🧩 Otherwise, normalize standard steps
    # =================================================================
    for step in plan:
        a = (step.get("action") or "").lower()
        t = (step.get("target") or "").strip()
        v = (step.get("value") or "").strip()

        # SauceDemo normalization
        if app_context == "sauce":
            if a == "fill" and "user" in v.lower():
                t, v = "#user-name", "standard_user"
            elif a == "fill" and ("pass" in v.lower() or "secret" in v.lower()):
                t, v = "#password", "secret_sauce"
            elif a in ["press", "click"] and not t:
                t = "#login-button"
            elif a == "find_and_click" and "add" in t.lower():
                t = "button.btn_inventory:has-text('Add to cart')"
            elif "shopping_cart" in t:
                t = ".shopping_cart_link"
            if t == "#login-button":
                fixed_plan.append({"action": a, "target": t, "value": v})
                fixed_plan.append({"action": "wait_for", "target": ".inventory_list", "value": ""})
                continue

        # TodoMVC normalization
        elif app_context == "todo":
            if a == "fill" and "input" in t:
                t = "input.new-todo"
            if "clear-completed" in t or "clear" in t:
                t = "button.clear-completed"

        fixed_plan.append({"action": a, "target": t, "value": v})

    # Add a default wait if none exists
    if app_context == "todo" and not any("input.new-todo" in s.get("target", "") for s in fixed_plan):
        fixed_plan.insert(0, {"action": "wait_for", "target": "input.new-todo", "value": ""})

    return fixed_plan


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def clean_yaml_block(text: str) -> str:
    """Robust cleaner for Markdown code fences (```yaml ... ```)."""
    import re

    # Strip whitespace and carriage returns
    text = text.strip()

    # Remove starting or embedded markdown fences like ```yaml, ```yml, or just ```
    text = re.sub(r"(?s)^```[a-zA-Z]*\s*", "", text)  # remove the first ``` block and following newline(s)
    text = re.sub(r"\s*```$", "", text)               # remove closing triple backticks if present

    # Clean residual formatting and trim
    return text.strip()


def normalize_plan_dict(plan_dict):
    """Ensure consistent list-of-dicts structure."""
    if isinstance(plan_dict, dict):
        plan_dict = [plan_dict]
    return plan_dict

# def generate_plan(task: str):
#     retriever = SimpleRetriever()
#     retrieved = retriever.retrieve(task)
#     context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

#     prompt = f"""
#     You are Agent B. Convert the user's task into a YAML DSL plan.
#     Available actions: open, find_and_click, fill, press, expect.
#     Task: {task}
#     Context from knowledge base:
#     {context}

#     Output YAML with keys: action, target, value (if any).
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2,
#     )

#     plan_yaml = response.choices[0].message.content.strip()
#     plan_yaml = clean_yaml_block(plan_yaml)
#     plan_dict = yaml.safe_load(plan_yaml)
#     plan_dict = normalize_plan_dict(plan_dict) 
#     return load_dsl_from_dict(plan_dict)


def generate_plan(task: str):
    retriever = SimpleRetriever()
    # retrieved = retriever.retrieve(task)
    # context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])
    # prompt = f"""
    # You are Agent B. Convert the user's task into a YAML DSL plan.
    # # Available actions: open, find_and_click, fill, press, expect.
    # Available actions:
    # - open → open a URL
    # - fill → type text into an input field
    # - press → press a keyboard key like ENTER
    # - find_and_click → click buttons or links
    # - expect → verify text or element is visible
    # - mark_completed → check off a todo item containing specified text
    # - delete_todo → delete a todo item containing specified text
    # - clear_completed → click the "Clear completed" button

    # Task: {task}
    # Context from knowledge base:
    # {context}

    # Output YAML with keys: action, target, value (if any).
    # """


    retrieved = retriever.retrieve(task)
    context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

    # 🔧 Inject app-specific selector hints to help the LLM plan better
    if "todo" in task.lower() or "todomvc" in task.lower():
        context += """
    Known selectors for TodoMVC:
    - new todo input: input.new-todo
    - todo list items: ul.todo-list li label
    - complete checkbox: input.toggle
    - clear completed button: button.clear-completed
    """
    elif "sauce" in task.lower() or "swag" in task.lower():
        context += """
    Known selectors for SauceDemo:
    - username field: #user-name
    - password field: #password
    - login button: #login-button
    """


    prompt = f"""
    You are Agent B, a precise automation planner.

    Task: {task}
    Context from knowledge base:
    {context}

    Generate a YAML plan with the minimal set of actions needed to complete ONLY the described task — 
    do not assume any extra follow-up steps (like checkout, add-to-cart, or logout) 
    unless explicitly mentioned.

    Valid actions: open, fill, press, find_and_click, expect, wait_for.
    Output YAML with keys: action, target, and value (if any).
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = response.choices[0].message.content.strip()

    # ✅ Always clean markdown first
    plan_yaml = clean_yaml_block(plan_yaml)

    # ✅ Add robust fallback if the YAML still fails
    try:
        plan_dict = yaml.safe_load(plan_yaml)
    except yaml.YAMLError:
        print("\n⚠️  YAML parse failed — retrying after cleaning again...\n")
        print("LLM Output before cleaning:\n", response.choices[0].message.content)
        plan_yaml = clean_yaml_block(plan_yaml)
        plan_dict = yaml.safe_load(plan_yaml)

    # plan_dict = normalize_plan_dict(plan_dict)
    # return load_dsl_from_dict(plan_dict)
    for step in plan_dict:
        if isinstance(step, dict) and isinstance(step.get("target"), str):
            step["target"] = step["target"].replace("#USER-NAME", "#user-name")
            step["target"] = step["target"].replace("#PASSWORD", "#password")
            step["target"] = step["target"].replace("#LOGIN-BUTTON", "#login-button")

    plan_dict = normalize_plan_dict(plan_dict)
    plan_dict = sanitize_plan(plan_dict)
    return load_dsl_from_dict(plan_dict)


# def repair_plan(failed_step, error_message, current_plan):
#     """Ask the LLM to repair or regenerate the plan after a failure."""
#     prompt = f"""
#     The previous plan failed at this step:
#     - action: {failed_step.action}
#       target: {failed_step.target}
#       value: {failed_step.value}

#     Error: {error_message}

#     Current plan:
#     {yaml.dump([s.__dict__ for s in current_plan])}

#     Please return a corrected YAML plan (only YAML, no markdown formatting).
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2,
#     )

#     plan_yaml = response.choices[0].message.content.strip()
#     plan_yaml = clean_yaml_block(plan_yaml)
#     plan_dict = yaml.safe_load(plan_yaml)
#     plan_dict = normalize_plan_dict(plan_dict)  
#     return load_dsl_from_dict(plan_dict)

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

    plan_yaml = response.choices[0].message.content.strip()
    plan_yaml = clean_yaml_block(plan_yaml)

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

# def clean_yaml_block(text: str) -> str:
#     """Remove Markdown code fences like ```yaml or ```."""
#     text = text.strip()
#     if text.startswith("```"):
#         text = text.split("```")[1] if "```" in text else text
#     text = text.replace("yaml", "", 1).strip()
#     return text


# def normalize_plan_dict(plan_dict):
#     """Filter or correct any invalid actions returned by the LLM."""
#     valid_actions = {"open", "find_and_click", "fill", "press", "expect", "wait_for"}
#     cleaned = []
#     for step in plan_dict:
#         if step.get("action") not in valid_actions:
#             # Try to interpret it heuristically
#             txt = step.get("action", "").lower()
#             if "click" in txt:
#                 step["action"] = "find_and_click"
#             elif "fill" in txt or "type" in txt or "input" in txt:
#                 step["action"] = "fill"
#             elif "open" in txt or "goto" in txt:
#                 step["action"] = "open"
#             elif "press" in txt or "enter" in txt:
#                 step["action"] = "press"
#             else:
#                 print(f"[yellow]Skipped invalid step: {step}[/yellow]")
#                 continue
#         cleaned.append(step)
#     return cleaned
