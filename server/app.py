import os
import mimetypes
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tools.vector_index import ingest_folder, search_index

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_ROOT = os.path.abspath(os.path.expanduser("~/Documents"))


class IngestBody(BaseModel):
    path: str


class QueryBody(BaseModel):
    query: str
    limit: int = 3


def extract_best_snippet(text: str, query: str, max_len: int = 280) -> str:
    raw = (text or "").strip().replace("\n", " ")
    if not raw:
        return ""

    keywords = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query or "") if len(w) > 1]
    if not keywords:
        return raw[:max_len] + ("…" if len(raw) > max_len else "")

    lower = raw.lower()
    best_pos = -1
    for kw in keywords:
        pos = lower.find(kw)
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1:
        return raw[:max_len] + ("…" if len(raw) > max_len else "")

    start = max(0, best_pos - 80)
    end = min(len(raw), best_pos + max_len - 80)
    snippet = raw[start:end].strip()

    if start > 0:
        snippet = "…" + snippet
    if end < len(raw):
        snippet = snippet + "…"

    return snippet


@app.post("/api/ingest")
def api_ingest(body: IngestBody):
    p = (body.path or "").replace("\r", "").replace("\n", "")
    if not p:
        return {"ok": False, "error": "Path is empty."}
    return ingest_folder(p)


@app.post("/api/search")
def api_search(body: QueryBody):
    results = search_index(body.query, limit=body.limit)
    return {"results": results}


@app.post("/api/answer")
def api_answer(body: QueryBody):
    results = search_index(body.query, limit=body.limit)

    if not results:
        return {
            "answer": "No matching documents found.",
            "sources": [],
        }

    best = results[0]
    snippet = extract_best_snippet(best.get("context", ""), body.query)

    return {
        "answer": snippet or "Found a matching document.",
        "sources": results,
    }


@app.get("/api/file")
def api_file(path: str = Query(...)):
    full_path = os.path.abspath(os.path.expanduser(path.replace("\r", "").replace("\n", "")))

    if not full_path.startswith(ALLOWED_ROOT):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(full_path)
    return FileResponse(
        full_path,
        media_type=mime_type or "application/octet-stream",
        filename=os.path.basename(full_path),
    )