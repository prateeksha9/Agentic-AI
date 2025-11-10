# app.py
import streamlit as st
import os
import glob
import time
import subprocess
from pathlib import Path

st.set_page_config(page_title="Agent B UI Executor", layout="wide")

st.title("🤖 Agent B — Live Task Executor")
st.write("Enter a task below, and Agent B will plan, execute, and capture the UI states step-by-step.")

task = st.text_input("📝 Enter task:", placeholder="e.g. add Buy milk and Pay bills to the todo app")

if st.button("Run Agent"):
    if not task.strip():
        st.warning("Please enter a task first.")
    else:
        st.info("🚀 Executing... please wait 1–2 minutes depending on browser load.")
        output = subprocess.run(["python", "main.py", task], capture_output=True, text=True)

        # Show terminal output
        st.subheader("🔧 Execution Log")
        st.code(output.stdout)

        # Locate the most recent run folder
        dataset_root = Path("dataset")
        latest_run = max(dataset_root.rglob("run_*"), key=os.path.getmtime, default=None)

        if latest_run:
            st.success(f"✅ Execution complete! Showing captured steps from: {latest_run}")
            image_files = sorted(glob.glob(str(latest_run / "*.png")))

            if image_files:
                for idx, img_path in enumerate(image_files, 1):
                    st.image(img_path, caption=f"Step {idx}: {os.path.basename(img_path)}", use_container_width=True)
                    # st.image(img_path, caption=f"Step {idx}: {os.path.basename(img_path)}", use_column_width=True)
                    st.divider()
                    time.sleep(0.1)
            else:
                st.warning("No screenshots found in the latest run folder.")
        else:
            st.error("No dataset folder found.")
