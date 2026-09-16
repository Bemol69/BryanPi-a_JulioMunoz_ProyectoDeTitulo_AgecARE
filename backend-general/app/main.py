"""AgeCare — API general (usuarios, pacientes, marketplace público)."""
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import RequestIdMiddleware, register_error_handlers
from app.routers import auth, caregiver, marketplace, patients

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="AgeCare General API",
    version="0.1.0",
    description="Registro, pacientes y marketplace público de AgeCare",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)
api.include_router(patients.router)
api.include_router(caregiver.router)
api.include_router(marketplace.router)
app.include_router(api)


@app.get("/health", tags=["Salud"])
async def health():
    return {"status": "ok", "service": get_settings().app_name}
