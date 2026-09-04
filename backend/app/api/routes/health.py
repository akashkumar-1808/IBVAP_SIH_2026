import logging
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from ...config import settings
from ...db.client import check_database_health

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall system health: ok, degraded, or unhealthy")
    environment: str
    app_name: str
    database_status: str = Field(..., description="Database status: healthy, degraded, unreachable, or not_configured")
    database_message: Optional[str] = None
    supabase_configured: bool


@router.get("/health", response_model=HealthResponse)
async def get_health(response: Response, check_db: bool = True):
    """
    Evaluates backend and database health status.
    Verifies reachability to Supabase PostgreSQL without exposing sensitive tokens.
    For lightweight hosting/cloud probes (e.g., Render), pass ?check_db=false to bypass network DB checks.
    """
    if check_db:
        db_status, db_message = await check_database_health()
    else:
        db_status, db_message = "skipped", "Database check skipped for lightweight probe"

    is_healthy = db_status in ("healthy", "not_configured", "skipped")
    overall_status = "ok" if is_healthy else "degraded" if db_status in ("degraded",) else "unhealthy"

    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        app_name=settings.APP_NAME,
        database_status=db_status,
        database_message=db_message,
        supabase_configured=settings.is_supabase_configured,
    )
