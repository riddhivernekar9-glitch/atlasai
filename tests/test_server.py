"""
Smoke tests for the FastAPI backend.

These tests spin up the app with FastAPI's TestClient (no real network) and
exercise the three core routes: /health, /api/ingest, /api/answer.

Mocking strategy
----------------
* ``tools.vector_index._embed``        – replaced with a lambda so sentence-
                                          transformers never loads during tests.
* ``tools.vector_index._app_data_dir`` – redirected to tmp_path so ChromaDB
                                          writes to a throwaway directory.
* ``tools.vector_index._reset_collection`` – called before / after each test
                                          that touches the real ChromaDB path
                                          so collections don't bleed between runs.
* ``server.app.search_index``          – patched directly in answer tests so
                                          we control the retrieval results.
* ``server.app._llm_answer``           – patched so no real OpenAI calls are
                                          made during CI.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# /api/ingest
# ---------------------------------------------------------------------------

def test_ingest_empty_path():
    resp = client.post("/api/ingest", json={"path": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "error" in body


def test_ingest_nonexistent_path():
    resp = client.post("/api/ingest", json={"path": "/tmp/atlas_does_not_exist_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False


def test_ingest_real_folder(tmp_path: Path):
    """Ingest a temp folder with one .txt file; expect ok=True with chunk count."""
    import tools.vector_index as vi

    doc = tmp_path / "sample.txt"
    doc.write_text("The employment sponsor is Acme Corp. Salary: AED 15,000 per month.")

    # Fake embeddings (384-dim zeros) so sentence-transformers never runs;
    # redirect ChromaDB to a throwaway directory under tmp_path.
    fake_embed = lambda texts: [[0.0] * 384 for _ in texts]  # noqa: E731

    vi._reset_collection()
    try:
        with patch.object(vi, "_embed", side_effect=fake_embed), \
             patch.object(vi, "_app_data_dir", return_value=tmp_path):
            vi._reset_collection()  # force re-create against tmp_path
            resp = client.post("/api/ingest", json={"path": str(tmp_path)})
    finally:
        vi._reset_collection()  # always clean up global singleton

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["count"] >= 1
    assert body["chunks"] >= 1


# ---------------------------------------------------------------------------
# /api/answer
# ---------------------------------------------------------------------------

def test_answer_no_index(tmp_path: Path):
    """When the collection is empty the answer route returns no-results."""
    import tools.vector_index as vi

    vi._reset_collection()
    try:
        with patch.object(vi, "_app_data_dir", return_value=tmp_path):
            vi._reset_collection()
            resp = client.post(
                "/api/answer", json={"query": "who is the sponsor", "limit": 3}
            )
    finally:
        vi._reset_collection()

    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert body["sources"] == []


def test_answer_with_index(tmp_path: Path):
    """
    /api/answer returns a non-empty answer and identifies the sponsor when
    search_index returns a relevant chunk (LLM call is mocked).
    """
    mock_results = [
        {
            "relative_path": "contract.txt",
            "path": str(tmp_path / "contract.txt"),
            "context": (
                "This employment contract is sponsored by Nathan & Nathan "
                "(Dynamic Employment Services L.L.C.). Monthly salary: AED 12,000."
            ),
            "score": 0.95,
            "doc_type": "Contract",
        }
    ]

    with patch("server.app.search_index", return_value=mock_results), \
         patch("server.app._llm_answer",
               return_value="The sponsor is Nathan & Nathan (Dynamic Employment Services L.L.C.)."):
        ans_resp = client.post(
            "/api/answer", json={"query": "who is the sponsor", "limit": 3}
        )

    assert ans_resp.status_code == 200
    body = ans_resp.json()
    assert body["answer"]              # non-empty
    assert len(body["sources"]) >= 1
    # Regex extraction should still find the sponsor in the chunk
    assert "Sponsor" in body.get("structured", {})


def test_answer_salary_extraction(tmp_path: Path):
    """Structured extraction picks up AED salary figures from the chunk."""
    mock_results = [
        {
            "relative_path": "payslip.txt",
            "path": str(tmp_path / "payslip.txt"),
            "context": "Your monthly salary is AED 8,500 as per your contract.",
            "score": 0.90,
            "doc_type": "Payroll",
        }
    ]

    with patch("server.app.search_index", return_value=mock_results), \
         patch("server.app._llm_answer",
               return_value="Your salary is AED 8,500 per month."):
        resp = client.post(
            "/api/answer", json={"query": "what is my salary", "limit": 3}
        )

    body = resp.json()
    assert resp.status_code == 200
    assert "Salary" in body.get("structured", {})


def test_answer_llm_fallback_no_key(tmp_path: Path):
    """When OPENAI_API_KEY is absent _llm_answer returns '' and the regex
    fallback produces the structured / snippet answer instead."""
    mock_results = [
        {
            "relative_path": "contract.txt",
            "path": str(tmp_path / "contract.txt"),
            "context": "Monthly salary: AED 5,000 per month.",
            "score": 0.80,
            "doc_type": "Payroll",
        }
    ]

    with patch("server.app.search_index", return_value=mock_results), \
         patch("server.app._llm_answer", return_value=""):
        resp = client.post(
            "/api/answer", json={"query": "what is my salary", "limit": 3}
        )

    body = resp.json()
    assert resp.status_code == 200
    # Fallback path should still produce a non-empty answer
    assert body["answer"]


# ---------------------------------------------------------------------------
# /api/file  (path-traversal guard)
# ---------------------------------------------------------------------------

def test_file_blocks_path_traversal():
    resp = client.get("/api/file", params={"path": "/etc/passwd"})
    # Must be 403 (outside home) or 404 — never 200
    assert resp.status_code in (403, 404)
