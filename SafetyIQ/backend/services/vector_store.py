"""
SafetyIQ — Vector Store Service
=================================
Manages ChromaDB collections for RAG pipelines.

Collections:
  incidents    — Historical incident and near-miss records
  regulations  — OISD/Factory Act/DGMS regulatory clauses

Production:
  - ChromaDB with persistent storage
  - Voyage-3 embeddings via Anthropic API
  - Auto-ingestion on first startup from JSON corpus

Author: SafetyIQ Team
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Production: import chromadb and voyageai
# import chromadb
# import voyageai


class VectorStoreService:
    """
    Thin wrapper around ChromaDB for incident and regulatory RAG.

    Demo mode: uses keyword-based search (no embeddings needed).
    Production: swap search methods to use ChromaDB .query() with embeddings.
    """

    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.persist_dir = Path(persist_dir)
        self._incidents: list[dict[str, Any]] = []
        self._regulations: list[dict[str, Any]] = []
        self._loaded = False

    def load(self, incidents: list[dict], regulations: list[dict]):
        """Load corpus into in-memory store (demo mode)."""
        self._incidents = incidents
        self._regulations = regulations
        self._loaded = True
        logger.info(
            f"VectorStore loaded: {len(incidents)} incidents, {len(regulations)} regulatory clauses"
        )

    def load_from_files(self, incidents_path: str, regulations_path: str):
        """Load from JSON files on disk."""
        with open(incidents_path) as f:
            incidents = json.load(f)
        with open(regulations_path) as f:
            regulations = json.load(f)
        self.load(incidents, regulations)

    def search_incidents(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Keyword-based incident search.
        Production: ChromaDB semantic search with voyage-3 embeddings.
        """
        if not self._loaded:
            logger.warning("VectorStore not loaded. Returning empty results.")
            return []

        query_lower = query.lower()
        keywords = [k for k in query_lower.split() if len(k) > 3]

        scored = []
        for incident in self._incidents:
            text = " ".join([
                incident.get("description", ""),
                " ".join(incident.get("root_causes", [])),
                " ".join(incident.get("contributing_factors", [])),
                incident.get("zone", ""),
            ]).lower()

            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, incident))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [inc for _, inc in scored[:n_results]]

    def search_regulations(self, query: str, n_results: int = 4) -> list[dict]:
        """
        Keyword-based regulatory search.
        Production: ChromaDB semantic search.
        """
        if not self._loaded:
            return []

        query_lower = query.lower()
        keywords = [k for k in query_lower.split() if len(k) > 3]

        scored = []
        for reg in self._regulations:
            text = " ".join([
                reg.get("content", ""),
                reg.get("title", ""),
                " ".join(reg.get("applies_to", [])),
            ]).lower()

            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, reg))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [reg for _, reg in scored[:n_results]]

    def upsert_incident(self, incident: dict[str, Any]):
        """Add or update an incident in the store."""
        existing_ids = {i.get("incident_id") for i in self._incidents}
        if incident.get("incident_id") in existing_ids:
            self._incidents = [
                incident if i.get("incident_id") == incident.get("incident_id") else i
                for i in self._incidents
            ]
        else:
            self._incidents.append(incident)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def stats(self) -> dict[str, int]:
        return {
            "incidents": len(self._incidents),
            "regulations": len(self._regulations),
        }


# Module-level singleton
vector_store = VectorStoreService()