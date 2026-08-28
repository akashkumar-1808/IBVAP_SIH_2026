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
        try:
            query = self._get_table().select("*").order("timestamp_utc", desc=True)
            if camera_id:
                query = query.eq("camera_id", camera_id)
            if priority:
                query = query.eq("priority", priority)
            if event_type:
                query = query.eq("event_type", event_type)

            res = query.range(offset, offset + limit - 1).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error querying events: {exc}")
            raise

    def acknowledge_event(self, event_id: str, acknowledged_by: str) -> Optional[Dict[str, Any]]:
        """Mark an event as operator acknowledged."""
        return self.update(
            event_id,
            {
                "is_acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.utcnow().isoformat(),
            },
        )
