import os
import mimetypes
import re
from collections import OrderedDict
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


def _clean_value(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .,:;")
    return value


def _find_first(patterns, text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            if m.lastindex:
                return _clean_value(m.group(1))
            return _clean_value(m.group(0))
    return None


def extract_sponsor(text: str) -> str | None:
    patterns = [
        r"sponsor(?:ed)?(?: by| is|:)?\s+([A-Z][A-Za-z&().,\-\/ ]{3,120})",
        r"employment sponsor(?: is|:)?\s+([A-Z][A-Za-z&().,\-\/ ]{3,120})",
        r"visa sponsor(?: is|:)?\s+([A-Z][A-Za-z&().,\-\/ ]{3,120})",
    ]
    value = _find_first(patterns, text)
    if value:
        return value

    if "nathan & nathan" in text.lower():
        return "Nathan & Nathan (Dynamic Employment Services L.L.C.)"

    return None


def extract_salary(text: str) -> str | None:
    patterns = [
        r"monthly salary(?: of| is|:)?\s*(AED\s*[\d,]+(?:\.\d+)?)",
        r"salary(?: of| is|:)?\s*(AED\s*[\d,]+(?:\.\d+)?)",
        r"notional monthly salary(?: of| is|:)?\s*(AED\s*[\d,]+(?:\.\d+)?)",
        r"(AED\s*[\d,]+(?:\.\d+)?)\s*(?:per month|monthly)",
    ]
    return _find_first(patterns, text)


def extract_visa_type(text: str) -> str | None:
    patterns = [
        r"(employment visa)",
        r"(residence visa)",
        r"(work permit)",
        r"visa type(?: is|:)?\s*([A-Za-z][A-Za-z \-]{3,80})",
    ]
    return _find_first(patterns, text)


def extract_insurance(text: str) -> str | None:
    patterns = [
        r"insurance(?: included| cover| coverage)?(?: is|:)?\s*([A-Za-z0-9 ,&().\-]{3,120})",
        r"medical insurance(?: is|:)?\s*([A-Za-z0-9 ,&().\-]{3,120})",
    ]
    return _find_first(patterns, text)


def wanted_fields(query: str) -> list[str]:
    q = (query or "").lower()
    fields = []

    if "sponsor" in q:
        fields.append("Sponsor")
    if "salary" in q or "pay" in q or "monthly salary" in q:
        fields.append("Salary")
    if "visa" in q:
        fields.append("Visa Type")
    if "insurance" in q or "medical" in q:
        fields.append("Insurance")

    return fields


def confidence_label(score: float) -> str:
    if score >= 8:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def build_structured_answer(query: str, results: list[dict]) -> tuple[OrderedDict, dict]:
    wanted = wanted_fields(query)
    if not wanted:
        return OrderedDict(), {}

    structured = OrderedDict()
    confidence = {}

    for field in wanted:
        best_value = None
        best_score = -1.0

        for r in results[:5]:
            text = r.get("context") or ""
            score = float(r.get("score", 0))

            if field == "Sponsor":
                value = extract_sponsor(text)
            elif field == "Salary":
                value = extract_salary(text)
            elif field == "Visa Type":
                value = extract_visa_type(text)
            elif field == "Insurance":
                value = extract_insurance(text)
            else:
                value = None

            if value and score > best_score:
                best_value = value
                best_score = score

        if best_value:
            structured[field] = best_value
            confidence[field] = confidence_label(best_score)

    return structured, confidence


def structured_to_text(structured: OrderedDict) -> str:
    if not structured:
        return ""
    return "\n".join(f"{k}: {v}" for k, v in structured.items())


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
            "structured": {},
            "confidence": {},
        }

    structured, confidence = build_structured_answer(body.query, results)

    if structured:
        answer_text = structured_to_text(structured)
    else:
        best = results[0]
        answer_text = extract_best_snippet(best.get("context", ""), body.query) or "Found a matching document."

    return {
        "answer": answer_text,
        "sources": results,
        "structured": structured,
        "confidence": confidence,
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