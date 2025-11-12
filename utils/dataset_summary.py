# utils/dataset_summary.py
import os
import json
import csv
from datetime import datetime
from pathlib import Path

def generate_summary(run_dir: str):
    """
    Aggregate all *.json metadata files in a run directory into dataset_summary.csv
    """
    run_path = Path(run_dir)
    summary_path = run_path / "dataset_summary.csv"

    rows = []
    for file in sorted(run_path.glob("*.json")):
        try:
            with open(file, "r") as f:
                meta = json.load(f)
            rows.append({
                "step": meta.get("step"),
                "action": meta.get("action"),
                "file_name": file.stem + ".png",
                "url": meta.get("url"),
                "title": meta.get("title"),
                "timestamp": meta.get("timestamp"),
            })
        except Exception as e:
            print(f" Skipping {file.name}: {e}")

    if not rows:
        print(" No metadata found to summarize.")
        return None

    # Sort by step number for readability
    rows.sort(key=lambda r: r["step"] or 0)

    # Write summary CSV
    with open(summary_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Dataset summary generated: {summary_path}")
    return summary_path


# Quick test utility
if __name__ == "__main__":
    latest_run = sorted(Path("dataset/todomvc").glob("run_*"))[-1]
    generate_summary(latest_run)
