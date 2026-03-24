from fastapi import APIRouter
from . import auth, users, projects, pipeline, ic, investors, verifications
from . import data_rooms, deal_rooms, analytics, events, integrations
from . import pis, pestel, ein

api_router = APIRouter()

api_router.include_router(auth.router,         prefix="/auth",          tags=["Auth"])
api_router.include_router(users.router,        prefix="/users",         tags=["Users"])
api_router.include_router(projects.router,     prefix="/projects",      tags=["Projects"])
api_router.include_router(pipeline.router,     prefix="/pipeline",      tags=["Pipeline"])
api_router.include_router(ic.router,           prefix="/ic",            tags=["Investment Committee"])
api_router.include_router(investors.router,    prefix="/investors",     tags=["Investors"])
api_router.include_router(verifications.router,prefix="/verifications", tags=["Verifications"])
api_router.include_router(data_rooms.router,   prefix="/data-rooms",    tags=["Data Rooms"])
api_router.include_router(deal_rooms.router,   prefix="/deal-rooms",    tags=["Deal Rooms"])
api_router.include_router(analytics.router,    prefix="/analytics",     tags=["Analytics"])
api_router.include_router(events.router,       prefix="/events",        tags=["Events"])
api_router.include_router(integrations.router, prefix="/integrations",  tags=["Integrations"])
api_router.include_router(pis.router,          prefix="/pis",           tags=["PIS"])
api_router.include_router(pestel.router,       prefix="/pestel",        tags=["PESTEL"])
api_router.include_router(ein.router,          prefix="/ein",           tags=["EIN"])
