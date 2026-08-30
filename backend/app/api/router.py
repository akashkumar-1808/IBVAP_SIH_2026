from fastapi import APIRouter
from .routes import health, events, evidence, cameras, streams, ws, scenarios

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(events.router)
api_router.include_router(evidence.router)
api_router.include_router(cameras.router)
api_router.include_router(streams.router)
api_router.include_router(ws.router)
api_router.include_router(scenarios.router)
