from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import logging

from .core.config import settings
from .core.database import Base, engine, SessionLocal
from .api.v1 import api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Alternative Investment Platform — manages Projects, Pipeline, IC, Investors, Data Rooms, Deal Rooms and more.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── DB init + seed admin ─────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_admin()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"AIP Platform started — API docs at /docs")


def _seed_admin():
    from .models.user import User, UserRole
    from .core.security import get_password_hash
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@aip.local").first():
            admin = User(
                email="admin@aip.local",
                full_name="AIP Admin",
                hashed_password=get_password_hash("Admin@AIP2024!"),
                role=UserRole.admin,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin created: admin@aip.local / Admin@AIP2024!")
    finally:
        db.close()


# ── Routes ────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

# AI Chat endpoint (standalone)
from fastapi import Depends
from .core.security import get_current_user
from .models.user import User as UserModel
from .services.ai_engine import ai_chat
from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    context: str = ""

@app.post("/api/v1/ai/chat")
async def chat(req: ChatRequest, current_user: UserModel = Depends(get_current_user)):
    answer = await ai_chat(req.question, req.context)
    return {"answer": answer}


# ── Health endpoints ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# ── Serve frontend SPA (if built) ────────────────────────────────────────
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(_frontend_dist):
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        index = os.path.join(_frontend_dist, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
