# agent/planner.py
import os, yaml
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def repair_plan(failed_step, error_message, current_plan):
    prompt = f"""
    The previous plan failed at this step:
    - action: {failed_step.action}
      target: {failed_step.target}
      value: {failed_step.value}

    Error: {error_message}

    Current plan:
    {yaml.dump([s.__dict__ for s in current_plan])}

    Please return a corrected YAML plan that fixes the issue and continues from this point.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    plan_yaml = response.choices[0].message.content.strip().strip("```yaml").strip("```")
    plan_dict = yaml.safe_load(plan_yaml)
    return load_dsl_from_dict(plan_dict)




def generate_plan(task: str):
    retriever = SimpleRetriever()
    retrieved = retriever.retrieve(task)
    context = "\n\n".join([f"{a.upper()}:\n{text}" for a, text in retrieved])

    prompt = f"""
    You are Agent B. Convert the user's task into a YAML DSL plan.
    Available actions: open, find_and_click, fill, press, expect.
    Task: {task}
    Context from knowledge base:
    {context}

    Notes:
    - When filling text inputs, use the visible placeholder or label text (e.g. "What needs to be done?").
    - Avoid generic selectors like 'input' or 'textbox'.

    Output YAML with keys: action, target, value (if any).
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = response.choices[0].message.content.strip()

    # ✅ Optional: Save raw LLM output to inspect later
    with open("generated_plan.yaml", "w") as f:
        f.write(plan_yaml)

    # ✅ Fix: Remove markdown fences (```yaml ... ```)
    if plan_yaml.startswith("```"):
        plan_yaml = plan_yaml.strip("`")
        plan_yaml = plan_yaml.replace("yaml\n", "", 1).replace("```", "")

    plan_dict = yaml.safe_load(plan_yaml)
    return load_dsl_from_dict(plan_dict)
