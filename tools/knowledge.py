from pathlib import Path
import json

KNOWLEDGE_DIR = Path.home() / "Library" / "Application Support" / "AtlasAI" / "knowledge"
INDEX_FILE = KNOWLEDGE_DIR / "index.jsonl"


def _load_index():
    if not INDEX_FILE.exists():
        return []

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def knowledge_search(query: str, limit: int = 5) -> str:
    query_lc = query.lower()
    results = []

    for entry in _load_index():
        text = entry.get("text_excerpt", "").lower()

        if query_lc in text or query_lc in entry.get("relative_path", "").lower():
            results.append(entry)

    if not results:
        return "❌ No matching documents found."

    out = []

    for i, r in enumerate(results[:limit], start=1):
        out.append(
            f"• ({i}) {r['relative_path']}\n"
            f"  {r['path']}\n"
            f"  ↳ {r.get('text_excerpt','').strip()}"
        )

    return "\n".join(out)


def knowledge_answer(query: str, limit: int = 5) -> dict:
    """
    Finds the best matching approved docs and returns structured data
    """

    hits_text = knowledge_search(query, limit)

    if not hits_text or "• (" not in hits_text:
        return {"found": False, "context": "", "sources": []}

    paths = []

    for line in hits_text.splitlines():
        line = line.strip()
        if line.startswith("/"):
            paths.append(line)

    sources = []
    chunks = []

    for p in paths[:limit]:

        try:
            txt = open(p, "r", encoding="utf-8", errors="ignore").read().strip()
        except Exception:
            continue

        try:
            rel = p.split("/01_APPROVED/", 1)[-1]
        except Exception:
            rel = p

        sources.append({"relative_path": rel, "path": p})

        chunks.append(f"[SOURCE: {rel}]\n{txt}")

    if not chunks:
        return {"found": False, "context": "", "sources": []}

    return {
        "found": True,
        "context": "\n\n".join(chunks),
        "sources": sources,
    }


def format_answer(result: dict) -> str:
    """
    Convert the structured answer into clean text for the UI
    """

    if not result or not result.get("found"):
        return "No approved information found."

    lines = []

    context = result.get("context", "").strip()

    if context:
        for line in context.splitlines():
            if not line.startswith("[SOURCE"):
                lines.append(line)

    sources = result.get("sources", [])

    if sources:
        lines.append("")
        lines.append("Sources:")

        for s in sources:
            rp = s.get("relative_path") or s.get("path") or "unknown"
            lines.append(f"- {rp}")

    return "\n".join(lines).strip()