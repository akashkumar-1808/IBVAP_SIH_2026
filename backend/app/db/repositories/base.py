import logging
from typing import List, Optional, Dict, Any, TypeVar, Generic
from ..client import get_supabase_client

logger = logging.getLogger(__name__)

T = TypeVar("T")

# In-memory storage table cache: table_name -> {item_id: record_dict}
_MEMORY_TABLES: Dict[str, Dict[str, Dict[str, Any]]] = {}
_UNAVAILABLE_TABLES: set = set()


class BaseRepository:
    """
    Base repository providing clean data access methods over Supabase PostgREST tables.
    Falls back gracefully to in-memory storage when running in local/demo mode without Supabase.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        if table_name not in _MEMORY_TABLES:
            _MEMORY_TABLES[table_name] = {}

    def _get_table(self):
        if self.table_name in _UNAVAILABLE_TABLES:
            return None
        client = get_supabase_client()
        if client is None:
            return None
        return client.table(self.table_name)

    def _handle_db_error(self, exc: Exception, action: str):
        err_msg = str(exc)
        if "PGRST205" in err_msg or "Could not find the table" in err_msg:
            if self.table_name not in _UNAVAILABLE_TABLES:
                _UNAVAILABLE_TABLES.add(self.table_name)
                logger.info(
                    f"Remote table '{self.table_name}' not found in Supabase schema. "
                    f"Seamlessly using high-performance local memory repository."
                )
        else:
            logger.warning(f"Error {action} {self.table_name} in DB: {exc}")

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single record by its primary ID."""
        table = self._get_table()
        if table is None:
            return _MEMORY_TABLES[self.table_name].get(str(item_id))

        try:
            res = table.select("*").eq("id", item_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        except Exception as exc:
            self._handle_db_error(exc, f"fetching by id '{item_id}'")
            return _MEMORY_TABLES[self.table_name].get(str(item_id))

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List records with pagination."""
        table = self._get_table()
        if table is None:
            items = list(_MEMORY_TABLES[self.table_name].values())
            return items[offset:offset + limit]

        try:
            res = table.select("*").range(offset, offset + limit - 1).execute()
            return res.data or []
        except Exception as exc:
            self._handle_db_error(exc, "listing")
            items = list(_MEMORY_TABLES[self.table_name].values())
            return items[offset:offset + limit]

    def insert(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a single record and return the created entity."""
        record_id = str(record_data.get("id") or record_data.get("evidence_id") or "")
        if record_id:
            _MEMORY_TABLES[self.table_name][record_id] = dict(record_data)

        table = self._get_table()
        if table is None:
            return record_data

        try:
            res = table.insert(record_data).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return record_data
        except Exception as exc:
            self._handle_db_error(exc, "inserting into")
            return record_data

    def update(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record by ID."""
        str_id = str(item_id)
        if str_id in _MEMORY_TABLES[self.table_name]:
            _MEMORY_TABLES[self.table_name][str_id].update(updates)

        table = self._get_table()
        if table is None:
            return _MEMORY_TABLES[self.table_name].get(str_id)

        try:
            res = table.update(updates).eq("id", item_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return _MEMORY_TABLES[self.table_name].get(str_id)
        except Exception as exc:
            self._handle_db_error(exc, f"updating id '{item_id}'")
            return _MEMORY_TABLES[self.table_name].get(str_id)

    def delete(self, item_id: str) -> bool:
        """Delete a record by ID."""
        str_id = str(item_id)
        _MEMORY_TABLES[self.table_name].pop(str_id, None)

        table = self._get_table()
        if table is None:
            return True

        try:
            table.delete().eq("id", item_id).execute()
            return True
        except Exception as exc:
            logger.warning(f"Error deleting from {self.table_name} id '{item_id}' in DB: {exc}")
            return True

