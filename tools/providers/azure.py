# tools/providers/azure.py
from __future__ import annotations

import os
from typing import Any, Dict, List

from .base import Provider, SourceChunk


class AzureProvider(Provider):
    """
    AzureProvider (Azure OpenAI Adapter Skeleton)
    ------------------------------------------------
    This is a *skeleton* provider.

    It lets us switch from LocalProvider -> AzureProvider later
    WITHOUT changing the rest of the app (UI + API stay the same).

    Required env vars later:
      - AZURE_OPENAI_ENDPOINT
      - AZURE_OPENAI_API_KEY
      - AZURE_OPENAI_API_VERSION (optional)
      - AZURE_OPENAI_CHAT_DEPLOYMENT
      - AZURE_OPENAI_EMBED_DEPLOYMENT
    """

    def __init__(self) -> None:
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
        self.embed_deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "")

    def ingest(self, folder: str) -> Dict[str, Any]:
        # Azure mode will still use the same indexing strategy unless we move indexing to Azure.
        return {
            "ok": False,
            "error": "AzureProvider ingest not implemented yet (skeleton). Use Local mode for now."
        }

    def search(self, query: str, limit: int = 5) -> List[SourceChunk]:
        # Later: use Azure embeddings + vector search (local or hosted).
        return []

    def answer(self, query: str, limit: int = 5) -> Dict[str, Any]:
        # Later: call Azure OpenAI chat completion using deployment name.
        return {
            "answer": "AzureProvider not connected yet (skeleton). Switch to local mode for now.",
            "sources": [],
            "raw": None,
        }