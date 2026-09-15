"""Catálogos del marketplace: perfiles de cuidadoras, artículos de apoyo,
reseñas, puntos de fidelización y ranking."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app import models
from app.audit import audit
from app.deps import Db, require, require_internal_key
from app.enums import CaregiverStatus, ContentStatus
from app.errors import conflict, invalid, not_found
from app.schemas.common import Page
from app.schemas.operation import (CaregiverOut, CaregiverPatchIn, CaregiverPointsIn,
                                   CaregiverPointsOut, CaregiverRankingItem, CaregiverReviewIn,
                                   CaregiverReviewOut, CaregiverSyncIn, ProductCreateIn, ProductOut,
                                   ProductPatchIn)
from app.security import now_utc

router = APIRouter(prefix="/marketplace", tags=["Catálogos marketplace"])

# Puntos de fidelización otorgados automáticamente al registrar una reseña.
POINTS_JOB_COMPLETED = 10
POINTS_GOOD_REVIEW_BONUS = 5
GOOD_REVIEW_THRESHOLD = 4


async def _total_points(db: Db, caregiver_id: UUID) -> int:
    total = (await db.execute(
        select(func.coalesce(func.sum(models.CaregiverPointsLog.points), 0))
        .where(models.CaregiverPointsLog.caregiver_id == caregiver_id))).scalar_one()
    return int(total)


def _cg_out(c: models.CaregiverProfile, include_note: bool = False) -> CaregiverOut:
    return CaregiverOut(caregiver_id=c.id, name=c.name, zone=c.zone,
                        specialties=c.specialties or [], languages=c.languages or [],
                        certifications_count=c.certifications_count, rating_avg=c.rating_avg,
                        reviews_count=c.reviews_count, status=CaregiverStatus(c.status),
                        submitted_at=c.submitted_at, reviewed_by_name=c.reviewed_by_name,
                        internal_note=c.internal_note if include_note else None)


# ---------- Sincronización desde el sitio público ----------
# Cuando una cuidadora publica su perfil en el sitio público, llega aquí como
# "pendiente" para que el staff la revise. Se autentica con una clave interna
# compartida (X-Internal-Key) en vez de un JWT de staff, porque quien llama es
# otro servicio, no una persona logueada.
@router.post("/caregivers/sync", response_model=CaregiverOut, status_code=201,
            dependencies=[Depends(require_internal_key)])
async def sync_caregiver(body: CaregiverSyncIn, db: Db):
    existing = (await db.execute(select(models.CaregiverProfile)
                                 .where(models.CaregiverProfile.email == body.email))).scalar_one_or_none()
    if existing is not None:
        # Solo se actualizan los datos descriptivos; el estado (aprobada/
        # suspendida) lo decide el staff y no se pisa desde el sitio público.
        existing.name = body.name
        existing.zone = body.zone
        existing.specialties = body.specialties
        existing.languages = body.languages
        existing.certifications_count = body.certifications_count
        return _cg_out(existing)

    profile = models.CaregiverProfile(name=body.name, email=body.email, zone=body.zone,
                                      specialties=body.specialties, languages=body.languages,
                                      certifications_count=body.certifications_count,
                                      certifications_verified=False, status="pending")
    db.add(profile)
    await db.flush()
    return _cg_out(profile)


# ---------- 10.1 Listar cuidadoras ----------
@router.get("/caregivers", response_model=Page[CaregiverOut], dependencies=[require("marketplace")])
async def list_caregivers(db: Db,
                          status_f: CaregiverStatus | None = Query(default=None, alias="status"),
                          zone: str | None = None,
                          specialty: str | None = None,
                          q: str | None = Query(default=None, max_length=120),
                          page: int = Query(default=1, ge=1),
                          page_size: int = Query(default=25, ge=1, le=100)):
    stmt = select(models.CaregiverProfile)
    if status_f:
        stmt = stmt.where(models.CaregiverProfile.status == status_f)
    if zone:
        stmt = stmt.where(models.CaregiverProfile.zone.ilike(f"%{zone}%"))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(models.CaregiverProfile.name.ilike(like) |
                          models.CaregiverProfile.email.ilike(like))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(models.CaregiverProfile.submitted_at.desc())
                             .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    if specialty:  # las especialidades viven en JSON; filtro en memoria sobre la página
        rows = [r for r in rows if specialty.lower() in [s.lower() for s in (r.specialties or [])]]
    return Page(items=[_cg_out(c) for c in rows], page=page, page_size=page_size, total=total)


# ---------- 10.2 Aprobar / suspender / anotar ----------
@router.patch("/caregivers/{caregiver_id}", response_model=CaregiverOut)
async def patch_caregiver(caregiver_id: UUID, body: CaregiverPatchIn, request: Request, db: Db,
                          admin: models.AdminUser = require("marketplace", write=True)):
    c = await db.get(models.CaregiverProfile, caregiver_id)
    if c is None:
        raise not_found()
    before = {"status": c.status}
    if body.status is not None:
        if body.status == CaregiverStatus.approved and not c.certifications_verified:
            raise conflict("CERTIFICATION_REQUIRED",
                           "No puede aprobarse un perfil sin certificación verificada.")
        if body.status == CaregiverStatus.suspended and not body.reason:
            raise invalid("REASON_REQUIRED", "Para suspender un perfil debes indicar el motivo.")
        c.status = body.status
        c.status_reason = body.reason
        c.reviewed_by = admin.id
        c.reviewed_by_name = admin.full_name
        # Al suspender se notificaría a la cuidadora con el motivo.
    if body.internal_note is not None:
        c.internal_note = body.internal_note
    await audit(db, request, "marketplace.caregiver_update", "caregiver_profile", c.id,
                before=before, after={"status": c.status})
    return _cg_out(c, include_note=True)


# ---------- Fidelización 1: ranking de cuidadoras por puntos ----------
@router.get("/caregivers/ranking", response_model=Page[CaregiverRankingItem],
           dependencies=[require("marketplace")])
async def caregiver_ranking(db: Db,
                            zone: str | None = None,
                            page: int = Query(default=1, ge=1),
                            page_size: int = Query(default=25, ge=1, le=100)):
    points_sub = (select(models.CaregiverPointsLog.caregiver_id,
                         func.sum(models.CaregiverPointsLog.points).label("points"))
                 .group_by(models.CaregiverPointsLog.caregiver_id).subquery())
    stmt = (select(models.CaregiverProfile, func.coalesce(points_sub.c.points, 0))
           .outerjoin(points_sub, points_sub.c.caregiver_id == models.CaregiverProfile.id)
           .where(models.CaregiverProfile.status == CaregiverStatus.approved))
    if zone:
        stmt = stmt.where(models.CaregiverProfile.zone.ilike(f"%{zone}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(func.coalesce(points_sub.c.points, 0).desc(),
                         models.CaregiverProfile.rating_avg.desc().nulls_last())
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
    items = [
        CaregiverRankingItem(rank=(page - 1) * page_size + i + 1, caregiver_id=c.id, name=c.name,
                             zone=c.zone, points=int(pts), rating_avg=c.rating_avg,
                             reviews_count=c.reviews_count, status=CaregiverStatus(c.status))
        for i, (c, pts) in enumerate(rows)
    ]
    return Page(items=items, page=page, page_size=page_size, total=total)


# ---------- 10.2b Detalle de una cuidadora ----------
@router.get("/caregivers/{caregiver_id}", response_model=CaregiverOut,
           dependencies=[require("marketplace")])
async def get_caregiver(caregiver_id: UUID, db: Db):
    c = await db.get(models.CaregiverProfile, caregiver_id)
    if c is None:
        raise not_found()
    return _cg_out(c, include_note=True)


# ---------- Fidelización 2: otorgar puntos manualmente ----------
@router.post("/caregivers/{caregiver_id}/points", response_model=CaregiverPointsOut, status_code=201)
async def award_points(caregiver_id: UUID, body: CaregiverPointsIn, request: Request, db: Db,
                       admin: models.AdminUser = require("marketplace", write=True)):
    c = await db.get(models.CaregiverProfile, caregiver_id)
    if c is None:
        raise not_found()
    if c.status != CaregiverStatus.approved:
        raise conflict("CAREGIVER_NOT_APPROVED",
                       "Solo se pueden otorgar puntos a cuidadoras con perfil aprobado.")
    log = models.CaregiverPointsLog(caregiver_id=c.id, points=body.points, reason=body.reason,
                                    note=body.note, awarded_by=admin.id, awarded_by_name=admin.full_name)
    db.add(log)
    await db.flush()
    total = await _total_points(db, c.id)
    await audit(db, request, "marketplace.points_awarded", "caregiver_profile", c.id,
               after={"points": body.points, "reason": body.reason, "total_points": total})
    return CaregiverPointsOut(caregiver_id=c.id, points_awarded=body.points, reason=body.reason,
                              total_points=total, created_at=log.created_at or now_utc())


# ---------- Fidelización 3: registrar reseña (dispara puntos automáticamente) ----------
@router.post("/reviews", response_model=CaregiverReviewOut, status_code=201)
async def create_review(body: CaregiverReviewIn, request: Request, db: Db,
                        admin: models.AdminUser = require("marketplace", write=True)):
    c = await db.get(models.CaregiverProfile, body.caregiver_id)
    if c is None:
        raise not_found()
    if c.status != CaregiverStatus.approved:
        raise conflict("CAREGIVER_NOT_APPROVED",
                       "Solo se puede reseñar a cuidadoras con perfil aprobado.")
    review = models.CaregiverReview(caregiver_id=c.id, family_name=body.family_name,
                                    rating=body.rating, comment=body.comment,
                                    job_reference=body.job_reference)
    db.add(review)
    await db.flush()

    # Ciclo de fidelización: toda reseña cierra un trabajo -> puntos base,
    # más un bono si la calificación es buena (>= GOOD_REVIEW_THRESHOLD).
    points_awarded = POINTS_JOB_COMPLETED
    db.add(models.CaregiverPointsLog(caregiver_id=c.id, points=POINTS_JOB_COMPLETED,
                                     reason="job_completed", review_id=review.id,
                                     note=f"Trabajo cerrado con reseña de {body.family_name}.",
                                     awarded_by=admin.id, awarded_by_name=admin.full_name))
    if body.rating >= GOOD_REVIEW_THRESHOLD:
        points_awarded += POINTS_GOOD_REVIEW_BONUS
        db.add(models.CaregiverPointsLog(caregiver_id=c.id, points=POINTS_GOOD_REVIEW_BONUS,
                                         reason="good_review", review_id=review.id,
                                         note=f"Bono por buena reseña (rating {body.rating}).",
                                         awarded_by=admin.id, awarded_by_name=admin.full_name))

    # Recalcular promedio y conteo de reseñas de la cuidadora.
    agg = (await db.execute(
        select(func.avg(models.CaregiverReview.rating), func.count(models.CaregiverReview.id))
        .where(models.CaregiverReview.caregiver_id == c.id))).one()
    c.rating_avg = round(float(agg[0]), 2) if agg[0] is not None else None
    c.reviews_count = int(agg[1])

    await audit(db, request, "marketplace.review_created", "caregiver_profile", c.id,
               after={"rating": body.rating, "points_awarded": points_awarded})
    return CaregiverReviewOut(id=review.id, caregiver_id=c.id, family_name=body.family_name,
                              rating=body.rating, comment=body.comment,
                              job_reference=body.job_reference, points_awarded=points_awarded,
                              created_at=review.created_at or now_utc())


# ---------- Fidelización 4: listar reseñas de una cuidadora ----------
@router.get("/caregivers/{caregiver_id}/reviews", response_model=Page[CaregiverReviewOut],
           dependencies=[require("marketplace")])
async def list_reviews(caregiver_id: UUID, db: Db,
                       page: int = Query(default=1, ge=1),
                       page_size: int = Query(default=25, ge=1, le=100)):
    c = await db.get(models.CaregiverProfile, caregiver_id)
    if c is None:
        raise not_found()
    stmt = (select(models.CaregiverReview).where(models.CaregiverReview.caregiver_id == caregiver_id)
           .order_by(models.CaregiverReview.created_at.desc()))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    items = []
    for r in rows:
        pts = (await db.execute(
            select(func.coalesce(func.sum(models.CaregiverPointsLog.points), 0))
            .where(models.CaregiverPointsLog.review_id == r.id))).scalar_one()
        items.append(CaregiverReviewOut(id=r.id, caregiver_id=r.caregiver_id,
                                        family_name=r.family_name, rating=r.rating,
                                        comment=r.comment, job_reference=r.job_reference,
                                        points_awarded=int(pts), created_at=r.created_at))
    return Page(items=items, page=page, page_size=page_size, total=total)


# ---------- 10.3 Listar artículos ----------
@router.get("/products", response_model=Page[ProductOut], dependencies=[require("marketplace")])
async def list_products(db: Db,
                        category: str | None = None,
                        status_f: ContentStatus | None = Query(default=None, alias="status"),
                        q: str | None = Query(default=None, max_length=120),
                        page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=25, ge=1, le=100)):
    stmt = select(models.Product)
    if category:
        stmt = stmt.where(models.Product.category.ilike(f"%{category}%"))
    if status_f:
        stmt = stmt.where(models.Product.status == status_f)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(models.Product.name.ilike(like) | models.Product.vendor.ilike(like))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(models.Product.updated_at.desc())
                             .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return Page(items=[ProductOut.model_validate(p) for p in rows],
                page=page, page_size=page_size, total=total)


# ---------- 10.4 Crear artículo ----------
@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(body: ProductCreateIn, request: Request, db: Db,
                         admin: models.AdminUser = require("marketplace", write=True)):
    p = models.Product(name=body.name, category=body.category, vendor=body.vendor,
                       price_clp=body.price_clp, external_url=str(body.external_url),
                       image_url=str(body.image_url) if body.image_url else None)
    db.add(p)
    await db.flush()
    await db.refresh(p)
    await audit(db, request, "marketplace.product_create", "product", p.id, after={"name": p.name})
    return ProductOut.model_validate(p)


# ---------- 10.5 Editar / archivar artículo ----------
@router.patch("/products/{product_id}", response_model=ProductOut)
async def patch_product(product_id: UUID, body: ProductPatchIn, request: Request, db: Db,
                        admin: models.AdminUser = require("marketplace", write=True)):
    p = await db.get(models.Product, product_id)
    if p is None:
        raise not_found()
    before = {"status": p.status, "name": p.name}
    if body.external_url is not None:
        if body.external_url.scheme != "https":
            raise invalid("INSECURE_URL", "El enlace externo debe usar https.")
        p.external_url = str(body.external_url)
    for field in ("name", "category", "vendor", "price_clp"):
        v = getattr(body, field)
        if v is not None:
            setattr(p, field, v)
    if body.image_url is not None:
        p.image_url = str(body.image_url)
    if body.status is not None:
        p.status = body.status
    p.updated_at = now_utc()
    await db.flush()
    await db.refresh(p)
    await audit(db, request, "marketplace.product_update", "product", p.id, before=before,
                after={"status": p.status, "name": p.name})
    return ProductOut.model_validate(p)
