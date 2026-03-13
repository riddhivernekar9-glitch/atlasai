from __future__ import annotations

import os
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import requests

from .base import SourceChunk
from tools.vector_index import build_index, semantic_search


# ----------------------------
# Small helpers
# ----------------------------
STOP = {
    "who", "what", "when", "where", "why", "how",
    "is", "are", "was", "were", "the", "a", "an",
    "of", "for", "to", "in", "on", "and", "or", "with",
    "please", "tell", "me", "about", "this", "that", "it",
}

def _simplify_query(q: str) -> str:
    q = (q or "").strip().lower()
    q = re.sub(r"[^a-z0-9\s&\-\_]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    toks = [t for t in q.split(" ") if t and t not in STOP]
    return " ".join(toks[:8]) if toks else q


def _extract_sponsor(text: str) -> Optional[str]:
    """
    Try to extract: Nathan & Nathan (Dynamic Employment Services L.L.C)
    from text without LLM as fallback.
    """
    if not text:
        return None

    # "with X (Y)"
    m = re.search(r"\bwith\s+([A-Z][A-Za-z0-9 &\.\-]+)\s*\(([^)]+)\)", text)
    if m:
        return f"{m.group(1).strip()} ({m.group(2).strip()})"

    # "sponsorship ... with X"
    m2 = re.search(r"sponsor(?:ship)?[^.\n]{0,160}\bwith\s+([A-Z][A-Za-z0-9 &\.\-]{2,80})", text, flags=re.I)
    if m2:
        return m2.group(1).strip()

    return None


def _ollama_available(base_url: str) -> bool:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=2)
        return r.ok
    except Exception:
        return False


def _ask_ollama(model: str, question: str, context: str, base_url: str) -> str:
    """
    Ollama local LLM call (FREE, no keys).
    """
    prompt = (
        "You are AtlasAI, a document intelligence assistant.\n"
        "Answer the question using ONLY the provided context.\n"
        "If the answer is not in the context, say: Not found in the provided documents.\n"
        "Be concise but specific.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }

    r = requests.post(f"{base_url}/api/generate", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()


class LocalProvider:
    """
    LocalProvider (FREE mode):
    - Ingest builds a local index into ./memory
    - Search uses semantic_search()
    - Answer uses:
        (A) Ollama local LLM (if running)  ✅ best quality
        (B) Fallback extractive answer (if Ollama not running)
    """

    def ingest(self, path: str) -> Dict[str, Any]:
        from pathlib import Path

        p = Path(path).expanduser().resolve()
        folder = p.parent if (p.exists() and p.is_file()) else p

        if not folder.exists() or not folder.is_dir():
            return {"ok": False, "error": f"Folder not found: {folder}"}

        return build_index(str(folder))

    def search(self, query: str, limit: int = 5) -> List[SourceChunk]:
        def run(q: str, k: int):
            return semantic_search(q, k=k) or []

        q0 = (query or "").strip()
        if not q0:
            return []

        # More forgiving retrieval
        results = run(q0, max(limit, 10))
        if not results:
            results = run(_simplify_query(q0), max(limit, 16))
        if not results:
            # bias common doc terms
            bias = []
            ql = q0.lower()
            for t in ["salary", "monthly", "aed", "insurance", "medical", "policy", "sponsor", "visa", "direct", "debit"]:
                if t in ql:
                    bias.append(t)
            qb = " ".join(bias + [_simplify_query(q0)]).strip()
            results = run(qb, max(limit, 24))

        out: List[SourceChunk] = []
        for r in results:
            out.append(
                SourceChunk(
                    relative_path=r.get("relative_path") or "",
                    path=r.get("path") or "",
                    score=float(r.get("score", 0.0)),
                    context=r.get("context", "") or "",
                )
            )
        return out

    def answer(self, query: str, limit: int = 5) -> Dict[str, Any]:
        chunks = self.search(query, limit=limit)

        if not chunks:
            return {"answer": "No matching content found.", "sources": [], "raw": []}

        sources = [asdict(c) for c in chunks]

        # Join context but keep it bounded
        context = "\n\n---\n\n".join([c.context for c in chunks])[:9000]

        # If sponsor question, try clean extraction first (nice quick win)
        ql = (query or "").lower()
        if "sponsor" in ql:
            sp = _extract_sponsor(context)
            if sp:
                return {"answer": sp, "sources": sources, "raw": sources}

        # Ollama LLM (FREE)
        base_url = os.getenv("ATLASAI_OLLAMA_URL", "http://127.0.0.1:11434")
        model = os.getenv("ATLASAI_OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

        print(f"[AtlasAI] Using Ollama at {base_url} with model {model}")
        if _ollama_available(base_url):
            try:
                ans = _ask_ollama(model=model, question=query, context=context, base_url=base_url)
                if ans:
                    return {"answer": ans, "sources": sources, "raw": sources}
            except Exception:
                # fall back below
                pass

        # Fallback (no Ollama running)
        best = (chunks[0].context or "").strip()
        best = best[:1200] if best else context[:1200]
        return {"answer": best, "sources": sources, "raw": sources}