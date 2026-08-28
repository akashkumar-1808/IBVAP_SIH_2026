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
async def get_health(response: Response):
    """
    Evaluates backend and database health status.
    Verifies reachability to Supabase PostgreSQL without exposing sensitive tokens.
    """
    db_status, db_message = await check_database_health()

    is_healthy = db_status in ("healthy", "not_configured")
    overall_status = "ok" if db_status == "healthy" else "degraded" if db_status in ("degraded", "not_configured") else "unhealthy"

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
