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
    settings.ensure_storage_directories()

    if settings.is_supabase_configured:
        async def _initial_db_check():
            try:
                db_status, msg = await check_database_health()
                logger.info(f"Initial Supabase DB check: status={db_status} msg={msg or 'ok'}")
            except Exception as exc:
                logger.warning(f"Initial Supabase DB check notice: {exc}")
        asyncio.create_task(_initial_db_check())
    else:
        logger.warning("Supabase credentials not set in environment. Running in unconfigured local mode.")

    # Start demo pipeline asynchronously so Uvicorn immediately binds to PORT and passes health checks
    from .api.routes.cameras import start_demo_pipeline_if_configured, stop_all_pipelines
    if getattr(settings, "AUTO_START_DEMO_PIPELINE", False):
        import threading
        def _async_start():
            try:
                start_demo_pipeline_if_configured()
            except Exception as exc:
                logger.error(f"Error during demo pipeline auto-start: {exc}")
        threading.Thread(target=_async_start, daemon=True, name="DemoPipelineAutoStart").start()

    yield

    # Shutdown lifecycle
    logger.info(f"Shutting down {settings.APP_NAME}...")
    try:
        stop_all_pipelines()
    except Exception as exc:
        logger.debug(f"Error stopping camera pipelines: {exc}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="IBVAP - Intelligent Border Video Analytics Platform API Backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Explicit CORS configuration for Render frontend and local development allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def api_key_auth_middleware(request: Request, call_next):
        """
        Prototype API Key authentication gate for browser-to-backend communication.
        Protects /api/v1/* endpoints while keeping /health, /, /docs, and static assets public.
        """
        path = request.url.path
        # Keep public endpoints, docs, static console, and CORS preflight OPTIONS unrestricted
        if (
            request.method == "OPTIONS"
            or path in ("/", "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico")
            or path.startswith("/health")
            or path.startswith("/console")
            or path.startswith("/assets")
        ):
            return await call_next(request)

        # Enforce authentication on protected API endpoints when API_KEY is configured
        if settings.get_api_key_value() and path.startswith(settings.API_V1_STR):
            token = request.headers.get("x-api-key")
            if not token:
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:].strip()
            if not token:
                token = request.query_params.get("api_key")

            if not settings.verify_api_token(token):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key. Access denied."},
                )

        return await call_next(request)

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
