import logging
from typing import Optional, Dict, Any, Tuple
from supabase import create_client, Client
from ..config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Returns a cached instance of the Supabase client initialized with the privileged
    service-role key (or anon key as fallback), or None if Supabase is not configured.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.is_supabase_configured:
        logger.warning("Supabase credentials not configured in environment; Supabase client unavailable.")
        return None

    url = settings.SUPABASE_URL
    key = settings.get_service_key_value() or settings.get_anon_key_value()

    if not url or not key:
        return None

    try:
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized successfully.")
        return _supabase_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        return None


def reset_supabase_client() -> None:
    """Resets the cached client (useful in tests and re-configurations)."""
    global _supabase_client
    _supabase_client = None


async def check_database_health() -> Tuple[str, Optional[str]]:
    """
    Performs an active check against the Supabase database.
    Returns a tuple of (status_string, optional_error_message).
    Status values: 'healthy', 'unreachable', 'not_configured'.
    Never leaks API keys or internal connection strings.
    """
    if not settings.is_supabase_configured:
        return "not_configured", "Supabase URL and API keys are not configured in environment"

    client = get_supabase_client()
    if client is None:
        return "unreachable", "Failed to initialize Supabase client instance"

    try:
        # Perform a lightweight ping query against the database via PostgREST
        # Query the 'cameras' table with a limit of 0 to verify connection & auth
        response = client.table("cameras").select("id", count="exact").limit(0).execute()
        return "healthy", None
    except Exception as exc:
        err_msg = str(exc)
        # Check if table doesn't exist yet (schema not applied) vs connection/auth failure
        if (
            "relation \"public.cameras\" does not exist" in err_msg.lower()
            or "42p01" in err_msg.lower()
            or "pgrst205" in err_msg.lower()
            or "could not find the table" in err_msg.lower()
        ):
            return "degraded", "Database connected but initial schema/migrations not yet applied"
        logger.warning(f"Database health check failed: {err_msg}")
        return "unreachable", "Database ping failed or rejected credentials"
