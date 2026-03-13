import json
from pathlib import Path

from tools import knowledge


def test_tokenize_and_scoring():
    toks = knowledge._tokenize("Hello, world 123")
    assert "hello" in toks

    item = {"relative_path": "docs/hello.md", "path": "/tmp/docs/hello.md", "text_excerpt": "Say hello world"}
    score = knowledge._score_item(["hello", "world"], item)
    assert score > 0


def test_knowledge_search_and_answer(tmp_path, monkeypatch):
    # write a temporary index file where knowledge expects it
    kd = Path.home() / "Library" / "Application Support" / "AtlasAI" / "knowledge"
    kd.mkdir(parents=True, exist_ok=True)
    idx = kd / "index.jsonl"
    record = {
        "relative_path": "notes/one.md",
        "path": str(kd / "notes" / "one.md"),
        "text_excerpt": "This is a test note about cats and dogs."
    }
    idx.write_text(json.dumps(record) + "\n", encoding="utf-8")

    res = knowledge.knowledge_search("cats")
    assert "notes/one.md" in res

    ans = knowledge.knowledge_answer("cats")
    assert ans["found"] is True
    assert len(ans["sources"]) >= 1
