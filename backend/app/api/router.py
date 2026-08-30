from fastapi import APIRouter
from .routes import health, events, evidence

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(events.router)
api_router.include_router(evidence.router)
