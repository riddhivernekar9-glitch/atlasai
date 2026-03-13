from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Protocol


@dataclass
class SourceChunk:
    relative_path: str
    path: str
    score: float
    context: str


class Provider(Protocol):
    """
    Provider (Adapter) interface.
    The rest of the app calls ONLY these methods.
    """

    def ingest(self, folder: str) -> Dict[str, Any]:
        ...

    def search(self, query: str, limit: int = 5) -> List[SourceChunk]:
        ...

    def answer(self, query: str, limit: int = 5) -> Dict[str, Any]:
        return {
            "answer": "...",
            "sources": [{"relative_path": "...", "path": "...", "score": 0.12}],
            "raw": None,
        }