# agent/planner.py
import os, yaml
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ─────────────────────────────────────────────
# 🧹 YAML Cleaning Utilities
# ─────────────────────────────────────────────
def clean_yaml_block(text: str) -> str:
    """Robust cleaner for Markdown code fences (```yaml ... ```)."""
    import re
    text = text.strip()
    text = re.sub(r"(?s)^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def normalize_plan_dict(plan_dict):
    """Ensure consistent list-of-dicts structure."""
    if isinstance(plan_dict, dict):
        plan_dict = [plan_dict]
    return plan_dict


# ─────────────────────────────────────────────
# 🧠 Plan Generator (LLM + RAG)
# ─────────────────────────────────────────────
# def generate_plan(task: str):
#     retriever = SimpleRetriever()
#     retrieved = retriever.retrieve(task)
#     context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

#     # -------------------------------------------------------------------------
#     # 🎯 Smarter prompt – context-aware for both SauceDemo & TodoMVC
#     # -------------------------------------------------------------------------
#     prompt = f"""
# You are Agent B, a precise automation planner.
# Convert the user's task into a **YAML DSL plan** for browser automation.

# Available actions:
#   - open → open a URL
#   - fill → type text into an input field
#   - press → press a keyboard key (e.g., ENTER)
#   - find_and_click → click a button or link
#   - expect → verify text or selector is visible
#   - mark_completed → check off a todo item
#   - delete_todo → delete a todo item
#   - clear_completed → click "Clear completed" button
#   - wait_for → pause briefly or wait for an element selector

# Task: {task}
# Context from knowledge base:
# {context}

# 🔹 SauceDemo rules
# - URL is https://www.saucedemo.com/
# - To log in, use:
#     fill → #user-name  standard_user
#     fill → #password   secret_sauce
#     find_and_click → #login-button
# - To verify success, use:
#     expect → .inventory_list
# - Only add/remove cart items if the task explicitly says so.
#   If the task is just “login”, stop after verifying login success.

# 🔹 TodoMVC rules
# - URL is https://demo.playwright.dev/todomvc
# - To add a task, use:
#     fill → input.new-todo
#     value → <task text>
#     press → ENTER
# - To mark a task done:
#     mark_completed → <task text>
# - To clear done tasks:
#     clear_completed → 
# - Never use visible text like "What needs to be done?" as a selector.

# Return ONLY valid YAML (no markdown fences) with keys:
#   - action
#   - target
#   - value (optional)
# """

#     # -------------------------------------------------------------------------
#     # 🧠 Generate with GPT-4o-mini
#     # -------------------------------------------------------------------------
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2,
#     )

#     plan_yaml = clean_yaml_block(response.choices[0].message.content.strip())

#     # -------------------------------------------------------------------------
#     # 🧩 Parse and normalize
#     # -------------------------------------------------------------------------
#     try:
#         plan_dict = yaml.safe_load(plan_yaml)
#     except yaml.YAMLError:
#         print("\n⚠️ YAML parse failed — retrying after cleaning again...\n")
#         plan_yaml = clean_yaml_block(plan_yaml)
#         plan_dict = yaml.safe_load(plan_yaml)

#     plan_dict = normalize_plan_dict(plan_dict)

#     # -------------------------------------------------------------------------
#     # 🧹 Post-filter for SauceDemo login-only tasks
#     # -------------------------------------------------------------------------
#     if (
#         "login" in task.lower() or "sign in" in task.lower()
#     ) and not any(x in task.lower() for x in ["add", "cart", "checkout"]):
#         filtered = []
#         for step in plan_dict:
#             tgt = str(step.get("target", "")).lower()
#             if any(w in tgt for w in ["add to cart", "remove", "shopping_cart", "cart_link"]):
#                 continue
#             filtered.append(step)
#         plan_dict = filtered
#         print("[blue]🧹 Trimmed extraneous SauceDemo actions after login[/blue]")

#     return load_dsl_from_dict(plan_dict)


def generate_plan(task: str):
    retriever = SimpleRetriever()
    retrieved = retriever.retrieve(task)
    context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

    # -------------------------------------------------------------------------
    # 🎯 Context-aware prompt for both SauceDemo and TodoMVC
    # -------------------------------------------------------------------------
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

🔹 SauceDemo Rules:
- URL: https://www.saucedemo.com/
- For login always use:
    - fill → #user-name   value: standard_user
    - fill → #password    value: secret_sauce
    - find_and_click → #login-button
    - expect → .inventory_list
- Only include add/remove cart steps if explicitly asked.

🔹 TodoMVC Rules:
- URL: https://demo.playwright.dev/todomvc
- To add tasks:
    - fill → input.new-todo
    - press → ENTER
- To mark tasks done:
    - mark_completed → <task name>
- To clear done tasks:
    - clear_completed → 
- Never use visible text like “What needs to be done?” as a selector.

Return ONLY valid YAML (no markdown fences).
Each step must include 'action' and 'target', and 'value' when needed.
"""

    # -------------------------------------------------------------------------
    # 🧠 Generate with GPT-4o-mini
    # -------------------------------------------------------------------------
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = clean_yaml_block(response.choices[0].message.content.strip())

    # -------------------------------------------------------------------------
    # 🧩 Parse safely
    # -------------------------------------------------------------------------
    try:
        plan_dict = yaml.safe_load(plan_yaml)
    except yaml.YAMLError:
        print("\n⚠️ YAML parse failed — retrying after cleaning again...\n")
        plan_yaml = clean_yaml_block(plan_yaml)
        plan_dict = yaml.safe_load(plan_yaml)

    plan_dict = normalize_plan_dict(plan_dict)

    # -------------------------------------------------------------------------
    # 🧹 Fix missing selectors automatically (LLM safety net)
    # -------------------------------------------------------------------------
    fixed = []
    for step in plan_dict:
        a = (step.get("action") or "").lower()
        t = (step.get("target") or "").strip()
        v = (step.get("value") or "").strip()

        # SauceDemo corrections
        if "sauce" in task.lower():
            if a == "fill" and v == "standard_user" and not t:
                t = "#user-name"
            elif a == "fill" and v == "secret_sauce" and not t:
                t = "#password"
            elif a == "find_and_click" and not t:
                t = "#login-button"
            elif a == "expect" and ("product" in v.lower() or not t):
                t = ".inventory_list"

        # TodoMVC corrections
        if "todo" in task.lower():
            if a == "fill" and not t:
                t = "input.new-todo"
            elif a == "expect" and not t and v:
                t = f"li:has-text('{v}')"

        fixed.append({"action": a, "target": t, "value": v})

    plan_dict = fixed

    # -------------------------------------------------------------------------
    # 🧽 Trim extra SauceDemo steps for login-only tasks
    # -------------------------------------------------------------------------
    if (
        "login" in task.lower() or "sign in" in task.lower()
    ) and not any(x in task.lower() for x in ["add", "cart", "checkout"]):
        filtered = []
        for step in plan_dict:
            tgt = str(step.get("target", "")).lower()
            if any(w in tgt for w in ["add to cart", "remove", "shopping_cart", "cart_link"]):
                continue
            filtered.append(step)
        plan_dict = filtered
        print("[blue]🧹 Trimmed extraneous SauceDemo actions after login[/blue]")

    return load_dsl_from_dict(plan_dict)




# ─────────────────────────────────────────────
# 🔧 Plan Repairer
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


# ─────────────────────────────────────────────
# 🔧 PLAN SANITIZER — Normalizes and fixes task-specific actions
# ─────────────────────────────────────────────
def sanitize_plan(plan):
    """
    Normalize and auto-correct plans for SauceDemo + TodoMVC.
    Adds robust handling for 'mark all completed' and 'complete all' tasks.
    """
    fixed_plan = []
    plan_text = str(plan).lower()

    # Detect which app we're dealing with
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
            {"action": "find_and_click", "target": "input.toggle", "value": ""},
            {"action": "wait_for", "target": "ul.todo-list li.completed", "value": ""},
            {"action": "expect", "target": "ul.todo-list li.completed", "value": ""},
        ]

    # =================================================================
    # 🧩 Default normalization for other tasks
    # =================================================================
    for step in plan:
        a = (step.get("action") or "").lower()
        t = (step.get("target") or "").strip()
        v = (step.get("value") or "").strip()

        # ---------- SauceDemo ----------
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

        # ---------- TodoMVC ----------
        elif app_context == "todo":
            if a == "fill" and "input" in t:
                t = "input.new-todo"
            if "clear-completed" in t or "clear" in t:
                t = "button.clear-completed"

        fixed_plan.append({"action": a, "target": t, "value": v})

    # Ensure we always start with an input wait for TodoMVC
    if app_context == "todo" and not any("input.new-todo" in s.get("target", "") for s in fixed_plan):
        fixed_plan.insert(0, {"action": "wait_for", "target": "input.new-todo", "value": ""})

    return fixed_plan
