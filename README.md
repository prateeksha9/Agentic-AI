# Agentic AI

This project implements **Agent B**, an intelligent browser automation system that can understand natural-language tasks such as
“Login to Sauce Demo with standard_user credentials” or “Add tasks in the Todo MVC app” and automatically perform them inside a real browser while capturing every UI state.

The system combines large-language-model reasoning, retrieval-augmented planning, and Playwright-based execution.
Each run produces a reproducible visual dataset showing every step of the workflow.

---

## Project Overview

When you run a command such as:

```bash
python main.py "Add backpack to cart in sauce demo"
```

Agent B will:

1. Parse the task using an OpenAI LLM plus a retrieval component.
2. Convert it into a structured YAML-style **DSL plan** (a list of browser actions such as open, fill, click, expect).
3. Execute the plan inside a Playwright browser.
4. Capture screenshots of each step.
5. Save cookies, localStorage, and browser state for continuity across runs.

---

## Folder Structure and Roles

### `agent/`

Core intelligence of the system.

* **`planner.py`** – Generates and sanitizes automation plans using OpenAI. It also adds specific rules for Sauce Demo and Todo MVC.
* **`executor.py`** – Executes the plan step-by-step inside the browser and logs results.
* **`capture.py`** – Saves screenshots for each step.

### `browser/`

Browser configuration and helpers.

* **`playwright_setup.py`** – Initializes Playwright, sets up isolated contexts, saves cookies, and restores browser state.

### `dsl/`

Domain-Specific Language definitions used to represent browser actions.

* **`schema.py`** – Pydantic model describing one action (action + target + value).
* **`parser.py`** – Converts YAML into validated Python DSL objects ready for execution.

### `rag/`

Retrieval-Augmented Generation layer.

* **`retriever.py`** – Uses a sentence-transformer model to retrieve relevant examples or prior tasks to guide the LLM.

### `utils/`

Helper utilities.

* **`dataset_summary.py`** – Builds a CSV summary of every step (timestamp, action, result) after each run.

### `dataset/`

Automatically generated output folder containing run-by-run results.
Each run includes:

* Step screenshots
* A CSV summary (`dataset_summary.csv`)
* Saved localStorage and cookie data

### `app.py`

A lightweight **Streamlit web interface** that lets you run Agent B visually.
You can enter a task, execute it, and instantly view the captured screenshots.

Run it with:

```bash
streamlit run app.py
```

### `main.py`

Command-line entry point.
It loads environment variables, invokes the planner, prints the generated plan, and triggers the executor.

### `.env`

Contains environment variables such as:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### `requirements.txt`

Lists all required Python packages to set up the project environment.

---

## Setting Up and Running the Project

### 1. Clone the repository

```bash
git clone https://github.com/yourname/softlight.git
cd softlight
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # for macOS / Linux
# or
.\.venv\Scripts\activate       # for Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install
```

### 5. Set your OpenAI API key

Create a file named `.env` in the project root and add:

```
OPENAI_API_KEY=sk-yourkeyhere
```

### 6. Run a test case from the command line

```bash
python main.py "Login to Sauce Demo with standard_user credentials"
```

### 7. (Optionally) Launch the Streamlit interface

```bash
streamlit run app.py
```

Then open the provided localhost URL in your browser and enter tasks interactively.

---

## Test Cases Executed

### Sauce Demo Tasks

1. Login to Sauce Demo with standard_user credentials
2. Add backpack to cart in Sauce Demo
3. Add backpack to cart and open cart page
4. Add backpack to cart, open cart page, and remove the backpack
5. Open the side menu in Sauce Demo and capture the menu options

### Todo MVC Tasks

6. Add “Buy laptop”, “Find job”, and “Take vacation” to Todo app
7. Mark “Buy laptop” as completed
8. Clear completed todos
9. Clear all todos
10. Filter to show only completed todos

Each task was converted into a structured DSL plan by `planner.py`, executed by `executor.py`, and recorded as screenshots in `dataset/`.

---

## Example Dataset Output

```
dataset/
 └── saucedemo/
      └── run_65_add_backpack_to_cart_in_sauce_demo/
           ├── 01_open.png
           ├── 02_fill_user.png
           ├── 03_click_login.png
           ├── 04_click_add_to_cart.png
           ├── dataset_summary.csv
```

You can open the Streamlit UI to visualize these steps one by one.

---

## Summary

Agent B demonstrates how a language-model-driven system can interpret instructions, plan structured actions, and autonomously execute them inside a browser while capturing every visual change.
The combination of retrieval guidance, rule-based corrections, Playwright automation, and a Streamlit viewer makes it a complete end-to-end example of intelligent, explainable web-workflow automation.

---

## Demo Videos
Full Workflow Demonstration

Link: https://drive.google.com/file/d/10AZ6aVv8UxlqFjudcZE43SgqRuK47yOq/view?usp=sharing

This video walks through how Agent B interprets a natural-language command, generates a plan through the LLM + RAG planner, and autonomously executes each step in a live browser while capturing intermediate UI states. It shows both Sauce Demo and TodoMVC tasks being planned, executed, and recorded into the dataset folder.

Streamlit UI Demo

Link: https://drive.google.com/file/d/1Yzd9XxYTEgvno09yyLXfcajkW966TGVp/view?usp=sharing

This short demo highlights the Streamlit interface (app.py) that lets you run Agent B interactively.
You can type a new task (e.g., “Add a todo and mark it completed”), trigger execution, and instantly visualize the screenshots captured from each UI step — without using the CLI.
