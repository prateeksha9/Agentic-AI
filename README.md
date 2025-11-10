# Softlight Agent 🤖

Agent B — a browser automation system that interprets natural-language tasks,
navigates web apps, and captures UI state screenshots.

## Quickstart
```bash
git clone <repo>
cd softlight-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install
python main.py "hello"
