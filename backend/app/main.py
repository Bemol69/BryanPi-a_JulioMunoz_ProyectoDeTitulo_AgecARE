"""AgeCare — API de la Consola de Administración (FastAPI + PostgreSQL)."""
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import RequestIdMiddleware, register_error_handlers
from app.routers import (auth, content, marketing, marketplace, metrics_commercial,
                         metrics_features, metrics_roles, moderation, ops, support)
from app.routers import system as system_router

app = FastAPI(
    title="AgeCare Admin API",
    version="1.0.0",
    description="Backend de la Consola de Administración de AgeCare · Wellq Co",
    docs_url="/api/v1/admin/docs",
    openapi_url="/api/v1/admin/openapi.json",
)
app.add_middleware(RequestIdMiddleware)
# CORS para el frontend local (React + Vite) del equipo Marketing y Fidelización.
# El backend base no lo traía porque no tenía frontend propio corriendo aún.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

api = APIRouter(prefix="/api/v1/admin")
api.include_router(auth.router)
api.include_router(metrics_commercial.router)
api.include_router(ops.router)
api.include_router(metrics_roles.router)
api.include_router(support.router)
api.include_router(metrics_features.router)
api.include_router(content.router)
api.include_router(marketplace.router)
api.include_router(marketing.router)
api.include_router(moderation.router)
api.include_router(system_router.router)
app.include_router(api)


@app.get("/health", tags=["Salud"])
async def health():
    return {"status": "ok", "service": get_settings().app_name}
