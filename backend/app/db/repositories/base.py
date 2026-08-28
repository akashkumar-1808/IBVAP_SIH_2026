import logging
from typing import List, Optional, Dict, Any, TypeVar, Generic
from ..client import get_supabase_client

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository:
    """
    Base repository providing clean data access methods over Supabase PostgREST tables.
    Encapsulates table operations and decouples API routes from raw database calls.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name

    def _get_table(self):
        client = get_supabase_client()
        if client is None:
            raise RuntimeError(f"Supabase client not initialized; cannot query table '{self.table_name}'")
        return client.table(self.table_name)

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single record by its primary ID."""
        try:
            res = self._get_table().select("*").eq("id", item_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as exc:
            logger.error(f"Error fetching {self.table_name} by id '{item_id}': {exc}")
            raise

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List records with pagination."""
        try:
            res = self._get_table().select("*").range(offset, offset + limit - 1).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error listing {self.table_name}: {exc}")
            raise

    def insert(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a single record and return the created entity."""
        try:
            res = self._get_table().insert(record_data).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return record_data
        except Exception as exc:
            logger.error(f"Error inserting into {self.table_name}: {exc}")
            raise

    def update(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record by ID."""
        try:
            res = self._get_table().update(updates).eq("id", item_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as exc:
            logger.error(f"Error updating {self.table_name} id '{item_id}': {exc}")
            raise

    def delete(self, item_id: str) -> bool:
        """Delete a record by ID."""
        try:
            self._get_table().delete().eq("id", item_id).execute()
            return True
        except Exception as exc:
            logger.error(f"Error deleting from {self.table_name} id '{item_id}': {exc}")
            raise
