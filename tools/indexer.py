import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

APP_NAME = "AtlasAI"

def app_support_dir() -> Path:
    home = Path.home()
    return home / "Library" / "Application Support" / APP_NAME

def knowledge_dir() -> Path:
    return app_support_dir() / "knowledge"

def safe_read_text(path: Path, max_bytes: int = 200_000) -> str:
    """
    Only reads plain-text-ish files safely.
    Keep it simple for v1: .txt, .md only.
    """
    if path.suffix.lower() not in {".txt", ".md"}:
        return ""

    try:
        data = path.read_bytes()
        data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_index(root: Path, out_jsonl: Path, out_manifest: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"❌ Root folder not found: {root}")

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    with out_jsonl.open("w", encoding="utf-8") as out:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue

            # skip hidden files
            if any(part.startswith(".") for part in path.parts):
                skipped += 1
                continue

            try:
                stat = path.stat()
                sha = file_sha256(path)

                rel = str(path.relative_to(root))
                text = safe_read_text(path)

                record = {
                    "id": sha[:16],  # short id
                    "sha256": sha,
                    "path": str(path),
                    "relative_path": rel,
                    "ext": path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified_utc": datetime.utcfromtimestamp(stat.st_mtime).isoformat(timespec="seconds") + "Z",
                    "indexed_utc": ts,
                    "text_excerpt": text[:2000],  # keep small for v1
                }

                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

            except Exception:
                skipped += 1
                continue

    manifest = {
        "root": str(root),
        "indexed_utc": ts,
        "files_indexed": count,
        "files_skipped": skipped,
        "index_file": str(out_jsonl),
        "notes": "v1 indexes metadata for all files; extracts text only from .txt/.md",
    }

    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

def main():
    parser = argparse.ArgumentParser(description="AtlasAI Knowledge Indexer (v1)")
    parser.add_argument("--root", required=True, help="Path to 01_APPROVED folder")
    args = parser.parse_args()

    root = Path(args.root)
    kd = knowledge_dir()
    out_jsonl = kd / "index.jsonl"
    out_manifest = kd / "manifest.json"

    manifest = build_index(root, out_jsonl, out_manifest)
    print("✅ Index built.")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()

