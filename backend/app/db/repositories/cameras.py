import logging
from typing import List, Optional, Dict, Any
from .base import BaseRepository

logger = logging.getLogger(__name__)


class CameraRepository(BaseRepository):
    """Repository managing 'cameras' table operations in Supabase PostgreSQL."""

    def __init__(self):
        super().__init__("cameras")

    def get_active_cameras(self) -> List[Dict[str, Any]]:
        """Fetch all cameras where is_active is true."""
        try:
            res = self._get_table().select("*").eq("is_active", True).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error fetching active cameras: {exc}")
            raise

    def update_stream_status(self, camera_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Update stream status (online, degraded, disconnected, offline)."""
        return self.update(camera_id, {"status": status})
