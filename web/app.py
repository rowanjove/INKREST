"""Main FastAPI application assembly and initialization."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from novel_agent.config.io import ConfigValidationError
from web.lifespan import lifespan
from web.websocket_manager import handle_websocket_tasks
from web.routes.projects import router as projects_router
from web.routes.chapters import router as chapters_router
from web.routes.assets import router as assets_router
from web.routes.prompts import router as prompts_router
from web.routes.config import router as config_router
from web.routes.database import router as database_router
from web.routes.assistant import router as assistant_router
from web.routes.covers import router as covers_router
from web.routes.outlines import router as outlines_router
from web.routes.agent_api import router as agent_api_router
from web.routes.factory import router as factory_router
from web.security import (
    ACCESS_TOKEN_ENV,
    ACCESS_TOKEN_HEADER,
    ALLOW_REMOTE_ENV,
    AccessTokenMiddleware,
    SecurityHeadersMiddleware,
    authorize_websocket,
    _tokens_match,
)
from web.routes.system import router as system_router
from web.routes.auth import router as auth_router
from web.routes.planning import router as planning_router
from web.routes.manuscript import router as manuscript_router
from web.routes.quality import router as quality_router
from web.routes.production import router as production_router
from web.routes.publishing import router as publishing_router
from web.routes.search import router as search_router

def _api_docs_enabled() -> bool:
    if os.environ.get(ALLOW_REMOTE_ENV, "").lower() in ("1", "true", "yes"):
        return os.environ.get("NOVEL_AGENT_DEBUG", "").lower() in ("1", "true", "yes")
    return True


_docs_enabled = _api_docs_enabled()
app = FastAPI(
    title="Novel Agent API",
    version="2.0.2",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AccessTokenMiddleware)

_logger = logging.getLogger("web.app")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    if not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(ConfigValidationError)
async def config_validation_exception_handler(
    request: Request, exc: ConfigValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "code": "CONFIG_INVALID",
            "message": "Pipeline configuration is invalid",
            "errors": exc.errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    _logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    if os.environ.get("NOVEL_AGENT_DEBUG", "").lower() in ("1", "true", "yes"):
        detail = str(exc).strip() or "服务器内部错误"
    else:
        detail = "服务器内部错误"
    return JSONResponse(status_code=500, content={"detail": detail})

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.websocket("/ws/tasks")
async def websocket_tasks(ws: WebSocket):
    """WebSocket endpoint for task progress."""
    if not await authorize_websocket(ws):
        return
    await handle_websocket_tasks(ws, accepted=True)


from web.routes.plugins import router as plugins_router

# Include domain routers
app.include_router(projects_router)
app.include_router(chapters_router)
app.include_router(assets_router)
app.include_router(prompts_router)
app.include_router(config_router)
app.include_router(database_router)
app.include_router(assistant_router)
app.include_router(plugins_router)
app.include_router(covers_router)
app.include_router(outlines_router)
app.include_router(agent_api_router)
app.include_router(factory_router)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(planning_router)
app.include_router(manuscript_router)
app.include_router(quality_router)
app.include_router(production_router)
app.include_router(publishing_router)
app.include_router(search_router)

if os.environ.get("E2E_FIXTURES", "").strip() in ("1", "true", "yes"):
    from web.routes.e2e_fixtures import router as e2e_fixtures_router

    app.include_router(e2e_fixtures_router)


def _require_enabled_web_extension(loaded_plugin) -> None:
    if not loaded_plugin.enabled:
        raise HTTPException(404, "Plugin web extension is disabled")


def _require_access_token(request: Request) -> None:
    expected = os.environ.get(ACCESS_TOKEN_ENV, "")
    if not expected:
        return
    supplied = request.headers.get(ACCESS_TOKEN_HEADER, "")
    if not _tokens_match(supplied, expected):
        raise HTTPException(401, "Invalid or missing access token")


_mounted_web_extensions = {}


def _enabled_web_extension_dependency(plugin_name: str):
    def require_enabled() -> None:
        loaded_plugin = _mounted_web_extensions.get(plugin_name)
        if loaded_plugin is None:
            raise HTTPException(404, "Plugin web extension is unavailable")
        _require_enabled_web_extension(loaded_plugin)

    return require_enabled


def mount_plugin_web_extensions(pm) -> None:
    """Mount newly discovered global web extension routes and refresh guards."""
    if not pm.allow_web_extensions:
        return
    for name, loaded in pm.plugins.items():
        if not loaded.enabled:
            continue
        ext = loaded.instance
        if name in _mounted_web_extensions:
            _mounted_web_extensions[name] = loaded
            continue
        if not hasattr(ext, "get_router"):
            continue
        plugin_router = ext.get_router()
        if plugin_router:
            previous_count = len(app.router.routes)
            app.include_router(
                plugin_router,
                dependencies=[
                    Depends(_require_access_token),
                    Depends(_enabled_web_extension_dependency(name)),
                ],
            )
            new_routes = app.router.routes[previous_count:]
            if new_routes:
                del app.router.routes[previous_count:]
                spa_index = next(
                    (index for index, route in enumerate(app.router.routes) if getattr(route, "name", "") == "serve_spa"),
                    len(app.router.routes),
                )
                app.router.routes[spa_index:spa_index] = new_routes
            _mounted_web_extensions[name] = loaded


# Include plugin web extension routers
try:
    from web.context import get_global_plugin_manager
    mount_plugin_web_extensions(get_global_plugin_manager())
except Exception as exc:
    _logger.warning("Plugin web extensions were not mounted: %s", exc)

# Serve Vue frontend
def _resolve_dist_dir() -> Optional[Path]:
    """Find valid frontend dist directory across source, PyInstaller, and Electron layouts."""
    candidates = []
    # 1. Direct source location (dev / normal run)
    candidates.append(Path(__file__).resolve().parent / "frontend" / "dist")
    # 2. PyInstaller _MEIPASS (single-file or unpacked)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "web" / "frontend" / "dist")
    # 3. Executable-relative _internal directory (PyInstaller onedir on Windows)
    exe_dir = Path(sys.executable).resolve().parent
    candidates.append(exe_dir / "_internal" / "web" / "frontend" / "dist")
    candidates.append(exe_dir / "web" / "frontend" / "dist")
    candidates.append(exe_dir / "frontend" / "dist")
    # 4. Explicit NOVEL_AGENT_ROOT override
    root_env = os.environ.get("NOVEL_AGENT_ROOT", "").strip()
    if root_env:
        candidates.append(Path(root_env) / "web" / "frontend" / "dist")

    for candidate in candidates:
        try:
            if candidate.is_dir() and (candidate / "index.html").is_file():
                return candidate
        except (OSError, PermissionError):
            continue
    return None


DIST_DIR = _resolve_dist_dir()

if DIST_DIR is not None:
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve static files or fall back to index.html for SPA routing."""
        # Never swallow unhandled API or WebSocket endpoints into index.html
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(404, "API endpoint not found")

        file_path = (DIST_DIR / full_path).resolve()
        try:
            file_path.relative_to(DIST_DIR.resolve())
        except ValueError:
            raise HTTPException(400, "Invalid path")

        if file_path.is_file():
            return FileResponse(str(file_path))

        index_file = DIST_DIR / "index.html"
        if not index_file.is_file():
            raise HTTPException(503, "Frontend bundle is missing index.html")
        return FileResponse(str(index_file))
else:
    @app.get("/")
    async def serve_missing_frontend():
        return JSONResponse(
            status_code=503,
            content={
                "code": "FRONTEND_NOT_BUILT",
                "message": "前端静态资源尚未构建或 index.html 缺失。请在 web/frontend 目录执行 npm run build 后重试。",
            },
        )
