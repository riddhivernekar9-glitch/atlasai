from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import hashlib
import json
import re

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

SKIP_DIR_NAMES = {
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "memory"
MEMORY_DIR.mkdir(exist_ok=True)
INDEX_FILE = MEMORY_DIR / "index.json"

STOPWORDS = {
    "who", "what", "where", "when", "why", "how",
    "is", "are", "was", "were", "do", "does", "did",
    "the", "a", "an", "and", "or", "of", "to", "in",
    "for", "on", "at", "with", "by", "from", "my",
    "your", "their", "our", "me", "we", "i"
}


def _should_index_file(p: Path) -> bool:
    if not p.exists() or not p.is_file():
        return False
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    parts = set(p.parts)
    if any(name in parts for name in SKIP_DIR_NAMES):
        return False

    return True


def _iter_indexable_files(path_or_folder: str) -> List[Path]:
    raw = (path_or_folder or "").replace("\r", "").replace("\n", "")
    base = Path(raw).expanduser()

    try:
        base = base.resolve()
    except Exception:
        return []

    if base.exists() and base.is_file():
        return [base] if _should_index_file(base) else []

    if not base.exists() or not base.is_dir():
        return []

    out: List[Path] = []
    for p in base.rglob("*"):
        if _should_index_file(p):
            out.append(p)

    return sorted(out)


def _read_text_file(p: Path) -> str:
    try:
        return p.read_text(errors="ignore")
    except Exception:
        return ""


def _read_pdf_file(p: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        text_parts: List[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts)
    except Exception:
        return ""


def _read_file(p: Path) -> str:
    if p.suffix.lower() == ".pdf":
        return _read_pdf_file(p)
    return _read_text_file(p)


def _chunk_text(text: str) -> List[str]:
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + CHUNK_SIZE, n)
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        start += max(1, CHUNK_SIZE - CHUNK_OVERLAP)

    return chunks


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_query(query: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]+", (query or "").lower())
    words = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return words


def classify_document(path: str, text: str) -> str:
    combined = f"{path}\n{text}".lower()

    # Strong signal rules (priority overrides)
    if any(x in combined for x in [
        "sponsor", "sponsorship", "employment visa", "residence permit", "work permit"
    ]):
        return "Visa"

    if any(x in combined for x in [
        "salary", "payroll", "wage", "compensation", "allowance"
    ]):
        return "Payroll"

    if any(x in combined for x in [
        "contract", "agreement", "terms and conditions", "probation", "termination"
    ]):
        return "Contract"

    if any(x in combined for x in [
        "insurance", "medical insurance", "coverage", "insured"
    ]):
        return "Insurance"

    if any(x in combined for x in [
        "law", "regulation", "compliance", "policy", "obligation"
    ]):
        return "Compliance"

    return "General"


def ingest_folder(folder_path: str, *args, **kwargs) -> Dict[str, Any]:
    files = _iter_indexable_files(folder_path)

    if not files:
        return {"ok": False, "error": "No valid files found."}

    index_data: List[Dict[str, Any]] = []
    total_chunks = 0
    files_seen = 0

    for p in files:
        content = _read_file(p)

        if not content.strip():
            content = f"Document file: {p.name}"

        doc_type = classify_document(str(p), content)

        chunks = _chunk_text(content)
        if not chunks:
            chunks = [f"Document file: {p.name}"]

        for chunk in chunks:
            index_data.append(
                {
                    "relative_path": p.name,
                    "path": str(p),
                    "context": chunk,
                    "score": 0.0,
                    "doc_type": doc_type,
                    "id": _hash_text(str(p) + "::" + chunk),
                }
            )

        total_chunks += len(chunks)
        files_seen += 1

    if not index_data:
        return {"ok": False, "error": "No extractable text or fallback content found."}

    INDEX_FILE.write_text(json.dumps(index_data, ensure_ascii=False))

    return {
        "ok": True,
        "folder": str(Path(folder_path).expanduser()),
        "count": files_seen,
        "chunks": total_chunks,
        "files": [str(f) for f in files],
    }


def search_index(query: str, limit: int = 3, *args, **kwargs) -> List[Dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []

    try:
        data = json.loads(INDEX_FILE.read_text(errors="ignore") or "[]")
    except Exception:
        return []

    raw_query = (query or "").strip().lower()
    if not raw_query:
        return []

    keywords = _normalize_query(raw_query)
    if not keywords:
        keywords = [raw_query]

    results: List[Dict[str, Any]] = []

    for item in data:
        ctx = (item.get("context") or "").lower()
        rel = (item.get("relative_path") or "").lower()
        path = (item.get("path") or "").lower()
        doc_type = (item.get("doc_type") or "").lower()

        score = 0.0

        if raw_query in ctx:
            score += 10.0
        if raw_query in rel or raw_query in path:
            score += 6.0
        if raw_query == doc_type:
            score += 8.0

        for kw in keywords:
            score += ctx.count(kw) * 2.0
            score += rel.count(kw) * 3.0
            score += path.count(kw) * 1.0
            score += doc_type.count(kw) * 2.0

        if score > 0:
            out = dict(item)
            out["score"] = score
            results.append(out)

    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[: max(1, int(limit))]