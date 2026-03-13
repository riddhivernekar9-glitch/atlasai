import os
import shutil

def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))

def create_folder(path: str) -> str:
    path = _expand(path)
    os.makedirs(path, exist_ok=True)
    return f"✅ Created/exists: {path}"

def list_files(path: str) -> str:
    path = _expand(path)
    if not os.path.exists(path):
        return f"❌ Path not found: {path}"
    if not os.path.isdir(path):
        return f"❌ Not a folder: {path}"

    items = sorted(os.listdir(path))
    preview = "\n".join(items[:200])
    more = "" if len(items) <= 200 else f"\n…(+{len(items)-200} more)"
    return f"📁 {path}\n{preview}{more}"

def find_files(query: str, path: str) -> str:
    path = _expand(path)
    if not os.path.isdir(path):
        return f"❌ Not a folder: {path}"

    q = (query or "").lower().strip()
    matches = []
    for root, _, files in os.walk(path):
        for f in files:
            if q in f.lower():
                matches.append(os.path.join(root, f))
                if len(matches) >= 200:
                    break
        if len(matches) >= 200:
            break

    if not matches:
        return f'🔎 No matches for "{query}" under {path}'
    return "🔎 Matches:\n" + "\n".join(matches)

def preview_move_matching(query: str, source_folder: str, extensions=None, 
limit: int = 200) -> str:
    source_folder = _expand(source_folder)
    if not os.path.isdir(source_folder):
        return f"❌ Not a folder: {source_folder}"

    q = "" if (query or "").strip() == "*" else (query or 
"").lower().strip()
    exts = None
    if extensions:
        exts = set(e.lower() if e.startswith(".") else "." + e.lower() for 
e in extensions)

    candidates = []
    for name in os.listdir(source_folder):
        p = os.path.join(source_folder, name)
        if not os.path.isfile(p):
            continue
        if q and q not in name.lower():
            continue
        if exts:
            _, ext = os.path.splitext(name)
            if ext.lower() not in exts:
                continue
        candidates.append(p)
        if len(candidates) >= limit:
            break

    if not candidates:
        return "No matching files found (nothing to move)."
    return "Would move:\n" + "\n".join(candidates)

def move_matching(query: str, source_folder: str, destination_folder: str, 
extensions=None, limit: int = 200) -> str:
    source_folder = _expand(source_folder)
    destination_folder = _expand(destination_folder)

    if not os.path.isdir(source_folder):
        return f"❌ Not a folder: {source_folder}"

    os.makedirs(destination_folder, exist_ok=True)

    q = "" if (query or "").strip() == "*" else (query or 
"").lower().strip()
    exts = None
    if extensions:
        exts = set(e.lower() if e.startswith(".") else "." + e.lower() for 
e in extensions)

    candidates = []
    for name in os.listdir(source_folder):
        p = os.path.join(source_folder, name)
        if not os.path.isfile(p):
            continue
        if q and q not in name.lower():
            continue
        if exts:
            _, ext = os.path.splitext(name)
            if ext.lower() not in exts:
                continue
        candidates.append(p)
        if len(candidates) >= limit:
            break

    if not candidates:
        return "No matching files to move."

    moved = []
    for src in candidates:
        dest = os.path.join(destination_folder, os.path.basename(src))
        shutil.move(src, dest)
        moved.append(dest)

    return "✅ Moved files:\n" + "\n".join(moved)

