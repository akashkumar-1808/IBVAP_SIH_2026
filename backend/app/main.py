import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.router import api_router
from .api.routes import health
from .db.client import get_supabase_client, check_database_health

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ibvap.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    import asyncio
    from .api.routes.ws import set_main_event_loop
    try:
        set_main_event_loop(asyncio.get_running_loop())
    except Exception:
        pass

    logger.info(f"Starting {settings.APP_NAME} in '{settings.ENVIRONMENT}' mode...")
    if settings.is_supabase_configured:
        db_status, msg = await check_database_health()
        logger.info(f"Initial Supabase DB check: status={db_status} msg={msg or 'ok'}")
    else:
        logger.warning("Supabase credentials not set in environment. Running in unconfigured local mode.")
    yield
    # Shutdown lifecycle
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="IBVAP - Intelligent Border Video Analytics Platform API Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration for React frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health endpoint and API v1 endpoints
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Mount compiled React Operator Console if dist exists
    import os
    from fastapi.staticfiles import StaticFiles

    dist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    if os.path.exists(dist_dir):
        app.mount("/console", StaticFiles(directory=dist_dir, html=True), name="console")
        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
    if os.path.exists(storage_dir):
        app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

    from fastapi import Request

    @app.get("/", tags=["Root"])
    async def root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept and os.path.exists(dist_dir):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/console")
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs",
            "console_url": "/console",
        }

    return app


app = create_app()
