import os
import subprocess
from pathlib import Path

def open_file(path: str) -> str:
    if not path:
        return "❌ open_file needs PATH:"

    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        return f"❌ File not found: {p}"

    # macOS: open with default app
    try:
        subprocess.run(["open", str(p)], check=False)
        return f"✅ Opened: {p}"
    except Exception as e:
        return f"❌ Could not open file: {e}"
