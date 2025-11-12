# agent/task_parser.py
from dsl.parser import load_dsl_from_dict

def parse_task_to_plan(task: str):
    task_lower = task.lower()

    if "notion" in task_lower and "create" in task_lower and "project" in task_lower:
        plan = [
            {"action": "open", "target": "https://www.notion.so"},
            {"action": "find_and_click", "target": "New"},
            {"action": "fill", "target": "Name", "value": "Example Project"},
            {"action": "press", "target": "Enter"},
            {"action": "expect", "target": "Project created"},
        ]

    # --- Sauce Demo login fix ---
    elif "sauce" in task_lower and ("login" in task_lower or "checkout" in task_lower):
        plan = [
            {"action":"open", "target":"https://www.saucedemo.com/"},
            {"action":"fill", "target":"#user-name", "value":"standard_user"},
            {"action":"fill", "target":"#password", "value":"secret_sauce"},
            {"action":"click", "target":"#login-button"},
            {"action":"expect", "target":".inventory_list"},
        ]

    elif "todo" in task_lower:
        # New test case: TodoMVC app (no login)
        plan = [
            {"action": "open", "target": "https://demo.playwright.dev/todomvc"},
            {"action": "fill", "target": "What needs to be done?", "value": "Buy milk"},
            {"action": "press", "target": "Enter"},
            {"action": "fill", "target": "What needs to be done?", "value": "Pay bills"},
            {"action": "press", "target": "Enter"},
            {"action": "expect", "target": "Buy milk"},
        ]

    else:
        plan = [
            {"action": "open", "target": "https://example.com"},
            {"action": "expect", "target": "Example Domain"},
        ]

    return load_dsl_from_dict(plan)