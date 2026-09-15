"""Sección 14 — Marketplace (vitrina de descubrimiento, sin transacciones)."""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app import models
from app.deps import CurrentUser, Db
from app.errors import conflict, forbidden, not_found
from app.schemas.common import Page
from app.schemas.marketplace import (CaregiverCardOut, CaregiverPublicOut, ContactIn, ContactOut,
                                     ProductCardOut, ProductOut, ReviewCreateIn, ReviewCreateOut,
                                     ReviewOut)

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


# ---------- 14.1 Buscar cuidadoras ----------
@router.get("/caregivers", response_model=Page[CaregiverCardOut])
async def search_caregivers(db: Db, user: CurrentUser,
                            q: str | None = Query(default=None, max_length=120),
                            zone: str | None = None,
                            specialty: str | None = None,
                            language: str | None = None,
                            min_rating: float | None = Query(default=None, ge=0, le=5),
                            page: int = Query(default=1, ge=1),
                            page_size: int = Query(default=20, ge=1, le=100)):
    if user.account_type != "family":
        raise forbidden("El marketplace de cuidadoras es para cuentas de familia.")
    stmt = (select(models.CaregiverProfile)
           .join(models.User, models.User.id == models.CaregiverProfile.user_id)
           .where(models.CaregiverProfile.is_listed.is_(True)))
    if q:
        stmt = stmt.where(models.User.full_name.ilike(f"%{q}%"))
    if min_rating is not None:
        stmt = stmt.where(models.CaregiverProfile.rating_avg >= min_rating)
    rows = (await db.execute(stmt)).scalars().all()

    def matches_list_field(value_list, needle):
        if not needle:
            return True
        return any(needle.lower() in v.lower() for v in (value_list or []))

    filtered = [c for c in rows if matches_list_field(c.zones, zone) and
               matches_list_field(c.specialties, specialty) and matches_list_field(c.languages, language)]
    filtered.sort(key=lambda c: (not c.is_featured, -(c.rating_avg or 0)))
    total = len(filtered)
    page_rows = filtered[(page - 1) * page_size: (page - 1) * page_size + page_size]
    items = [CaregiverCardOut(profile_id=c.id, full_name=c.user.full_name, photo_url=c.user.avatar_url,
                              headline=c.headline, years_experience=c.years_experience,
                              specialties=c.specialties or [], zones=c.zones or [],
                              rating_avg=c.rating_avg, reviews_count=c.reviews_count,
                              is_featured=c.is_featured) for c in page_rows]
    return Page(items=items, total=total)


async def _get_listed(db: Db, profile_id: UUID) -> models.CaregiverProfile:
    p = await db.get(models.CaregiverProfile, profile_id)
    if p is None or not p.is_listed:
        raise not_found("El perfil solicitado no existe.")
    return p


# ---------- 14.2 Perfil público de cuidadora ----------
@router.get("/caregivers/{profile_id}", response_model=CaregiverPublicOut)
async def get_caregiver_public(profile_id: UUID, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("El marketplace de cuidadoras es para cuentas de familia.")
    p = await _get_listed(db, profile_id)
    reviews = (await db.execute(select(models.CaregiverReview)
                                .where(models.CaregiverReview.caregiver_profile_id == profile_id)
                                .order_by(models.CaregiverReview.created_at.desc()))).scalars().all()
    return CaregiverPublicOut(
        profile_id=p.id, headline=p.headline, bio=p.bio, years_experience=p.years_experience,
        specialties=p.specialties or [], languages=p.languages or [], zones=p.zones or [],
        certifications=p.certifications or [], rating_avg=p.rating_avg, reviews_count=p.reviews_count,
        is_listed=p.is_listed, is_featured=p.is_featured, full_name=p.user.full_name,
        photo_url=p.user.avatar_url,
        reviews=[ReviewOut(review_id=r.id, rating=r.rating, comment=r.comment,
                          author_name=r.author_name, created_at=r.created_at) for r in reviews])


# ---------- 14.3 Contactar cuidadora ----------
@router.post("/caregivers/{profile_id}/contact", response_model=ContactOut, status_code=201)
async def contact_caregiver(profile_id: UUID, body: ContactIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede contactar a una cuidadora.")
    p = await _get_listed(db, profile_id)
    since = date.today() - timedelta(days=1)
    dup = (await db.execute(select(models.ContactRequest).where(
        models.ContactRequest.caregiver_profile_id == profile_id,
        models.ContactRequest.family_user_id == user.id,
        models.ContactRequest.created_at >= since))).scalar_one_or_none()
    if dup is not None:
        raise conflict("CONTACT_ALREADY_SENT", "Ya enviaste una solicitud de contacto a esta cuidadora hoy.")
    db.add(models.ContactRequest(caregiver_profile_id=profile_id, family_user_id=user.id,
                                 message=body.message))
    contact_value = p.user.phone or p.user.email
    channel = "phone" if p.user.phone else "email"
    return ContactOut(contact_channel=channel, contact_value=contact_value)


# ---------- 14.4 Calificar cuidadora ----------
@router.post("/caregivers/{profile_id}/reviews", response_model=ReviewCreateOut, status_code=201)
async def review_caregiver(profile_id: UUID, body: ReviewCreateIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede dejar una reseña.")
    p = await _get_listed(db, profile_id)
    already = (await db.execute(select(models.CaregiverReview).where(
        models.CaregiverReview.caregiver_profile_id == profile_id,
        models.CaregiverReview.author_user_id == user.id))).scalar_one_or_none()
    if already is not None:
        raise conflict("ALREADY_REVIEWED", "Ya dejaste una reseña para esta cuidadora.")

    review = models.CaregiverReview(caregiver_profile_id=profile_id, author_user_id=user.id,
                                    author_name=user.full_name, rating=body.rating, comment=body.comment)
    db.add(review)
    await db.flush()

    agg = (await db.execute(select(func.avg(models.CaregiverReview.rating),
                                   func.count(models.CaregiverReview.id))
                            .where(models.CaregiverReview.caregiver_profile_id == profile_id))).one()
    p.rating_avg = round(float(agg[0]), 2)
    p.reviews_count = int(agg[1])
    return ReviewCreateOut(review_id=review.id)


# ---------- 14.5 Catálogo de artículos de apoyo ----------
@router.get("/products", response_model=Page[ProductCardOut])
async def list_products(db: Db, user: CurrentUser,
                        category: str | None = None,
                        q: str | None = Query(default=None, max_length=120),
                        page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=20, ge=1, le=100)):
    stmt = select(models.MarketProduct)
    if category:
        stmt = stmt.where(models.MarketProduct.category == category)
    if q:
        stmt = stmt.where(models.MarketProduct.name.ilike(f"%{q}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    items = [ProductCardOut(product_id=p.id, name=p.name, category=p.category,
                            thumbnail_url=p.thumbnail_url, price_range=p.price_range) for p in rows]
    return Page(items=items, total=total)


# ---------- 14.6 Ficha de producto ----------
@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: Db, user: CurrentUser):
    p = await db.get(models.MarketProduct, product_id)
    if p is None:
        raise not_found()
    return ProductOut(product_id=p.id, name=p.name, category=p.category, description=p.description,
                      photos=p.photos or [], price_range=p.price_range, external_url=p.external_url,
                      contact_info=p.contact_info)
