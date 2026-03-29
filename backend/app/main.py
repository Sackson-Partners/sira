"""
SIRA Platform - Main Application Entry Point
Shipping Intelligence & Risk Analytics Platform

Serves both the API (/api/*) and the frontend SPA (all other routes).
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import time

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db, engine, Base
from app.core.limiter import limiter
from app.api import api_router

# 10 MB request body limit (applies to JSON payloads; file uploads use MAX_FILE_SIZE in config)
_MAX_REQUEST_BODY = 10 * 1024 * 1024

# Frontend dist directory
# Docker: /app/app/main.py → parent.parent = /app → /app/frontend/dist
# Local:  backend/app/main.py → parent.parent = backend/ → need to go up one more
_app_dir = Path(__file__).resolve().parent.parent
FRONTEND_DIR = _app_dir / "frontend" / "dist"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = _app_dir.parent / "frontend" / "dist"

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _ensure_admin_user():
    """Create admin user if it doesn't exist.

    Reads the initial password from the ADMIN_INITIAL_PASSWORD environment variable.
    Raises RuntimeError and refuses to start in production if the variable is not set.
    """
    import os
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    admin_password = os.getenv("ADMIN_INITIAL_PASSWORD")
    if not admin_password:
        if not settings.DEBUG:
            raise RuntimeError(
                "ADMIN_INITIAL_PASSWORD environment variable is not set. "
                "Set a strong, unique password before starting in production."
            )
        logger.warning(
            "ADMIN_INITIAL_PASSWORD not set — using insecure placeholder. "
            "Set the variable before deploying to production."
        )
        admin_password = "changeme-set-ADMIN_INITIAL_PASSWORD"

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                email="admin@sira.com",
                full_name="SIRA Administrator",
                hashed_password=hash_password(admin_password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created successfully")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error ensuring admin user: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting SIRA Platform API...")
    try:
        init_db()
        _ensure_admin_user()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed (app will start anyway): {e}")
    logger.info(f"SIRA Platform API v{settings.APP_VERSION} started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SIRA Platform API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## SIRA Platform API

    **Shipping Intelligence & Risk Analytics Platform**
    **Multimodal Control Tower + Fleet Management + Market Intelligence + AI**

    Sponsored by: Energie Partners (EP)

    ### Core Modules:
    - **Multimodal Control Tower**: Real-time operational visibility across all assets and corridor segments
    - **Vessel Tracking**: AIS-integrated vessel position tracking and charter management
    - **Fleet & Asset Management**: Truck, rail, barge, and equipment lifecycle management with dispatch
    - **Port & Terminal Operations**: Berth allocation, anchorage management, and congestion tracking
    - **Shipment Workspace**: End-to-end shipment tracking with milestones and exception management
    - **Market Intelligence**: Freight rate benchmarks, market indices, and demurrage analytics
    - **Chain-of-Custody**: Digital seals, audit trails, and tamper-evident custody tracking
    - **SIRA AI**: ETA prediction, demurrage risk scoring, and anomaly detection

    ### Legacy Modules:
    - **Security Intelligence**: Monitor events, manage alerts, and investigate incidents
    - **Case Management**: Handle security cases with evidence tracking
    - **Playbook System**: Standardized incident response procedures
    - **Real-time Notifications**: WebSocket and email alerts

    ### Authentication:
    All endpoints (except `/health` and `/api/v1/auth/token`) require authentication.
    Use the `/api/v1/auth/token` endpoint to obtain an access token.
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — origins controlled by ALLOWED_ORIGINS environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def enforce_request_size(request: Request, call_next):
    """Reject requests whose Content-Length exceeds 10 MB."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_REQUEST_BODY:
        return JSONResponse(
            status_code=413,
            content={"error": "Request body too large", "code": "REQUEST_TOO_LARGE"},
        )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Attach security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    # Tight CSP: API-only origin — no inline scripts, no external resources
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Attach X-Process-Time to every response for performance monitoring."""
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.time() - start:.4f}"
    return response


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Structured JSON for all HTTP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": f"HTTP_{exc.status_code}"},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured JSON for request validation failures.
    Only expose field-level details in DEBUG mode to avoid leaking schema info.
    """
    content: dict = {"error": "Request validation failed", "code": "VALIDATION_ERROR"}
    if settings.DEBUG:
        content["details"] = exc.errors()
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all: log the full trace server-side, return opaque 500 to client."""
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# Health check endpoint — must respond fast for Railway healthcheck
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    from datetime import datetime, timezone

    result = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Try DB check but don't block if it's slow/unavailable
    try:
        from app.core.database import check_db_connection
        db_ok = check_db_connection()
        result["database"] = "healthy" if db_ok else "unhealthy"
        if not db_ok:
            result["status"] = "degraded"
    except Exception as e:
        result["database"] = "unhealthy"
        result["status"] = "degraded"
        if settings.DEBUG:
            result["database_error"] = str(e)

    return result


# Include API router (must be before SPA catch-all)
app.include_router(api_router, prefix="/api")

# --- Frontend SPA serving ---
# Mount frontend static assets (JS/CSS bundles)
if FRONTEND_DIR.exists() and (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="static-assets")
    logger.info(f"Serving frontend assets from {FRONTEND_DIR / 'assets'}")


# SPA catch-all: serve index.html for all non-API routes
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    """Serve the React SPA for all non-API routes"""
    # If frontend is built, serve index.html
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    # Fallback: API info (no frontend built)
    return JSONResponse({
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Shipping Intelligence & Risk Analytics Platform",
        "docs": "/docs",
        "health": "/health",
    })


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
