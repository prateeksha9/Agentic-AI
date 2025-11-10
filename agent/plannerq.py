# agent/planner.py
import os, yaml
from openai import OpenAI
from rag.retriever import SimpleRetriever
from dsl.parser import load_dsl_from_dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    Output YAML with keys: action, target, value (if any).
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    plan_yaml = response.choices[0].message.content.strip()
    plan_dict = yaml.safe_load(plan_yaml)
    return load_dsl_from_dict(plan_dict)
