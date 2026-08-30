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
        try:
            res = self._get_table().select("*").eq("event_id", event_id).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error fetching evidence records for event '{event_id}': {exc}")
            return []

    def get_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """Finds an evidence record by exact SHA-256 fingerprint."""
        try:
            res = self._get_table().select("*").eq("sha256", sha256_hash).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as exc:
            logger.error(f"Error fetching evidence record by SHA-256 '{sha256_hash}': {exc}")
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
        try:
            query = self._get_table().select("*").order("created_at", desc=True)
            if camera_id:
                query = query.eq("camera_id", camera_id)
            if event_id:
                query = query.eq("event_id", event_id)
            if evidence_type:
                query = query.eq("evidence_type", evidence_type)
            if status:
                query = query.eq("status", status)

            res = query.range(offset, offset + limit - 1).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error querying evidence records: {exc}")
            return []
