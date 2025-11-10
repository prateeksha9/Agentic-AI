# main.py
import typer
from rich import print
from agent.executor import run_executor
import re

# 👉 Import the new intelligent planner
try:
    from agent.planner import generate_plan
    USE_LLM = True
except ImportError:
    from agent.task_parser import parse_task_to_plan
    USE_LLM = False

app = typer.Typer(help="Agent B – Autonomous Browser Agent with RAG Planner")

@app.command()
def run(task: str):
    print(f"[bold blue]Agent B starting...[/bold blue]")
    print(f"Received task: [green]{task}[/green]\n")

    # Phase 5: dynamic planning
    if USE_LLM:
        print("[cyan]Using LLM + RAG Planner to generate DSL plan...[/cyan]")
        plan = generate_plan(task)
    else:
        print("[yellow]LLM planner not available – using fallback parser.[/yellow]")
        from agent.task_parser import parse_task_to_plan
        plan = parse_task_to_plan(task)

    # Log the generated plan
    print("[yellow]Generated DSL Plan:[/yellow]")
    for step in plan:
        print(f"  • [cyan]{step.action}[/cyan] → {step.target or ''} {step.value or ''}")

    # Execute in browser
    print("\n[magenta]Executing plan in browser...[/magenta]\n")
    # run_executor(plan)

    first_url = next((step.target for step in plan if step.action == "open"), None)

    if first_url:
        if "saucedemo" in first_url:
            app_name = "saucedemo"
        elif "todomvc" in first_url:
            app_name = "todomvc"
        else:
            app_name = "generic"
    else:
        app_name = "generic"

    run_executor(plan, app_name, task_description=task)


if __name__ == "__main__":
    app()
