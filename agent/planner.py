# agent/planner.py
import os, yaml
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def clean_yaml_block(text: str) -> str:
#     """Remove Markdown code fences (```yaml ... ```)."""
#     if "```" in text:
#         text = text.replace("```yaml", "").replace("```yml", "").replace("```", "")
#     return text.strip()


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
    retrieved = retriever.retrieve(task)
    context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

    prompt = f"""
    You are Agent B. Convert the user's task into a YAML DSL plan.
    # Available actions: open, find_and_click, fill, press, expect.
    Available actions:
    - open → open a URL
    - fill → type text into an input field
    - press → press a keyboard key like ENTER
    - find_and_click → click buttons or links
    - expect → verify text or element is visible
    - mark_completed → check off a todo item containing specified text
    - delete_todo → delete a todo item containing specified text
    - clear_completed → click the "Clear completed" button

    Task: {task}
    Context from knowledge base:
    {context}

    Output YAML with keys: action, target, value (if any).
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

    plan_dict = normalize_plan_dict(plan_dict)
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




# inside generate_plan() after getting plan_yaml:

