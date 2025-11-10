# agent/capture.py
import os, json, hashlib, time
from datetime import datetime
from PIL import Image
import imagehash

def _hash_dom(page_content: str) -> str:
    """Create a quick hash of the DOM to detect changes."""
    return hashlib.md5(page_content.encode("utf-8")).hexdigest()

async def capture_state(page, step_idx: int, action: str, app_name="todomvc"):
    """Capture a screenshot + metadata for the current UI state."""
    # Prepare folders
    base_dir = f"dataset/{app_name}/run_{datetime.now().strftime('%Y%m%d')}"
    os.makedirs(base_dir, exist_ok=True)

    # Screenshot
    img_path = os.path.join(base_dir, f"{step_idx:02d}_{action}.png")
    await page.screenshot(path=img_path, full_page=True)

    # DOM + hash
    html = await page.content()
    dom_hash = _hash_dom(html)

    # Perceptual hash to catch near-duplicates
    phash = str(imagehash.phash(Image.open(img_path)))

    # Metadata
    meta = {
        "step": step_idx,
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "url": page.url,
        "title": await page.title(),
        "dom_hash": dom_hash,
        "phash": phash,
    }
    meta_path = img_path.replace(".png", ".json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"📸 Captured: {img_path}")
