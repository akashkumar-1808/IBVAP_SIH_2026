import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseRepository

logger = logging.getLogger(__name__)


class EventRepository(BaseRepository):
    """Repository managing 'events' table operations in Supabase PostgreSQL."""

    def __init__(self):
        super().__init__("events")

    def query_events(
        self,
        camera_id: Optional[str] = None,
        priority: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query security events with multi-criteria filtering."""
        table = self._get_table()
        if table is not None:
            try:
                query = table.select("*").order("created_at", desc=True)
                if camera_id:
                    query = query.eq("camera_id", camera_id)
                if priority:
                    query = query.eq("priority", priority)
                if event_type:
                    query = query.eq("event_type", event_type)

                res = query.range(offset, offset + limit - 1).execute()
                if res.data:
                    return res.data
            except Exception as exc:
                self._handle_db_error(exc, "querying")

        from .base import _MEMORY_TABLES
        events = list(_MEMORY_TABLES.get("events", {}).values())
        if camera_id:
            events = [e for e in events if e.get("camera_id") == camera_id]
        if priority:
            events = [e for e in events if str(e.get("priority")).upper() == priority.upper()]
        if event_type:
            events = [e for e in events if str(e.get("event_type")).lower() == event_type.lower()]

        # Sort by created_at desc
        events.sort(key=lambda e: str(e.get("created_at") or e.get("timestamp_utc") or ""), reverse=True)
        return events[offset:offset + limit]

    def acknowledge_event(self, event_id: str, acknowledged_by: str) -> Optional[Dict[str, Any]]:
        """Mark an event as operator acknowledged."""
        return self.update(
            event_id,
            {
                "is_acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.utcnow().isoformat(),
                "status": "RESOLVED",
            },
        )
