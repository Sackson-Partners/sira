"""
SIRA Platform - WSGI-Compatible Entry Point
For PythonAnywhere deployment (no async lifespan)

Serves both the API (/api/*) and the frontend SPA (all other routes).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
import logging
import os

from app.core.config import settings
from app.core.database import init_db
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Frontend dist directory (built Vite output)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# Create FastAPI application (without lifespan for WSGI compatibility)
app = FastAPI(
    title=settings.APP_NAME,
    description="SIRA Platform API - Shipping Intelligence & Risk Analytics",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Initialize database and seed admin user on import
try:
    init_db()
    logger.info("Database initialized")

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    admin_password = os.getenv("ADMIN_INITIAL_PASSWORD")
    if not admin_password:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "ADMIN_INITIAL_PASSWORD must be set in production. "
                "Refusing to start with no admin credentials."
            )
        logger.warning("ADMIN_INITIAL_PASSWORD not set — using placeholder (dev only).")
        admin_password = "changeme-set-ADMIN_INITIAL_PASSWORD"

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@sira.com",
                full_name="SIRA Administrator",
                hashed_password=hash_password(admin_password),
                role="admin",
                is_active=True,
                must_change_password=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created from ADMIN_INITIAL_PASSWORD env var.")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error seeding admin: {e}")
        db.rollback()
    finally:
        db.close()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

# CORS middleware — origins from ALLOWED_ORIGINS env var (no wildcard in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every response (mirrors app/main.py)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
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


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/health", tags=["Health"])
async def health_check():
    from datetime import datetime, timezone
    from app.core.database import check_db_connection
    db_status = "healthy" if check_db_connection() else "unhealthy"
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.APP_VERSION,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Include API router
app.include_router(api_router, prefix="/api")

# Serve frontend static assets (JS, CSS, images)
if FRONTEND_DIR.exists() and (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="static-assets")
    logger.info(f"Serving frontend from {FRONTEND_DIR}")
else:
    logger.warning(f"Frontend dist not found at {FRONTEND_DIR}")


# SPA catch-all: serve index.html for any non-API route
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not built. Run: cd frontend && npm run build"}
    )
