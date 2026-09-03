"""
Repository for managing 'evidence_records' table in Supabase PostgreSQL.

Architecture Decision: DEC-0008
"""

import logging
from typing import List, Optional, Dict, Any
from .base import BaseRepository

logger = logging.getLogger(__name__)


class EvidenceRepository(BaseRepository):
    """Repository managing 'evidence_records' operations in Supabase PostgreSQL."""

    def __init__(self):
        super().__init__("evidence_records")

    def get_by_event_id(self, event_id: str) -> List[Dict[str, Any]]:
        """Retrieves all evidence records associated with an event."""
        table = self._get_table()
        if table is not None:
            try:
                res = table.select("*").eq("event_id", event_id).execute()
                if res.data:
                    return res.data
            except Exception as exc:
                self._handle_db_error(exc, f"fetching evidence records for event '{event_id}'")

        from .base import _MEMORY_TABLES
        recs = list(_MEMORY_TABLES.get("evidence_records", {}).values())
        return [r for r in recs if r.get("event_id") == event_id]

    def get_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """Finds an evidence record by exact SHA-256 fingerprint."""
        table = self._get_table()
        if table is not None:
            try:
                res = table.select("*").eq("sha256", sha256_hash).limit(1).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as exc:
                self._handle_db_error(exc, f"fetching evidence record by SHA-256 '{sha256_hash}'")

        from .base import _MEMORY_TABLES
        for r in _MEMORY_TABLES.get("evidence_records", {}).values():
            if r.get("sha256") == sha256_hash:
                return r
        return None

    def query_evidence(
        self,
        camera_id: Optional[str] = None,
        event_id: Optional[str] = None,
        evidence_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query evidence items with multi-criteria filtering."""
        table = self._get_table()
        if table is not None:
            try:
                query = table.select("*").order("created_at", desc=True)
                if camera_id:
                    query = query.eq("camera_id", camera_id)
                if event_id:
                    query = query.eq("event_id", event_id)
                if evidence_type:
                    query = query.eq("evidence_type", evidence_type)
                if status:
                    query = query.eq("status", status)

                res = query.range(offset, offset + limit - 1).execute()
                if res.data:
                    return res.data
            except Exception as exc:
                self._handle_db_error(exc, "querying evidence records")

        from .base import _MEMORY_TABLES
        recs = list(_MEMORY_TABLES.get("evidence_records", {}).values())
        if camera_id:
            recs = [r for r in recs if r.get("camera_id") == camera_id]
        if event_id:
            recs = [r for r in recs if r.get("event_id") == event_id]
        if evidence_type:
            recs = [r for r in recs if r.get("evidence_type") == evidence_type]
        if status:
            recs = [r for r in recs if r.get("status") == status]

        return recs[offset:offset + limit]

