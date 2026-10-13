"""Sección 14 — Marketplace (vitrina de descubrimiento, sin transacciones)."""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app import models
from app.deps import CurrentUser, Db
from app.chat_retention import purge_expired
from app.errors import conflict, forbidden, not_found
from app.routers.chat import add_message, get_or_create_conversation
from app.schemas.common import Page
from app.schemas.marketplace import (CaregiverCardOut, CaregiverPublicOut, ContactIn, ContactOut,
                                     HireRequestIn, MyHireRequestOut, HireRequestOut, ProductCardOut, ProductOut, ReviewCreateIn,
                                     ReviewCreateOut, ReviewOut)
from app.security import as_utc, now_utc
from app.sync import sync_caregiver_to_admin, sync_review_to_admin

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


async def _is_engaged(db: Db, caregiver_profile_id) -> bool:
    active = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == caregiver_profile_id,
        models.CaregiverEngagement.status == "active"))).first()
    return active is not None


async def _family_display_name(db: Db, user: models.User, patient_id) -> str:
    """Arma "Familia <apellido>" a partir del adulto mayor a cargo, en vez del
    nombre de quien escribe la reseña o contrata: así se identifica al núcleo
    familiar, no a la persona puntual que usó la cuenta."""
    stmt = select(models.PatientMember).where(models.PatientMember.user_id == user.id)
    if patient_id is not None:
        stmt = stmt.where(models.PatientMember.patient_id == patient_id)
    member = (await db.execute(stmt)).scalars().first()
    if member is None and patient_id is not None:
        raise forbidden("No tienes acceso a ese perfil de adulto mayor.")
    surname = (member.patient.full_name if member else user.full_name).split()[-1]
    return f"Familia {surname}"


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
           .where(models.CaregiverProfile.is_listed.is_(True),
                  models.CaregiverProfile.admin_status == "approved"))
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
    engaged_ids = {r[0] for r in (await db.execute(
        select(models.CaregiverEngagement.caregiver_profile_id)
        .where(models.CaregiverEngagement.status == "active"))).all()}
    # Las que no están trabajando van primero; dentro de cada grupo, destacadas y mejor calificadas.
    filtered.sort(key=lambda c: (c.id in engaged_ids, not c.is_featured, -(c.rating_avg or 0)))
    total = len(filtered)
    page_rows = filtered[(page - 1) * page_size: (page - 1) * page_size + page_size]
    items = [CaregiverCardOut(profile_id=c.id, full_name=c.user.full_name, photo_url=c.user.avatar_url,
                              headline=c.headline, years_experience=c.years_experience,
                              specialties=c.specialties or [], zones=c.zones or [],
                              rating_avg=c.rating_avg, reviews_count=c.reviews_count,
                              is_featured=c.is_featured, is_engaged=c.id in engaged_ids) for c in page_rows]
    return Page(items=items, total=total)


async def _get_listed(db: Db, profile_id: UUID) -> models.CaregiverProfile:
    p = await db.get(models.CaregiverProfile, profile_id)
    if p is None or not p.is_listed or p.admin_status != "approved":
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
    my_engagement = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == profile_id,
        models.CaregiverEngagement.family_user_id == user.id,
        models.CaregiverEngagement.status == "active"))).scalars().first()
    can_review = (await db.execute(select(models.CaregiverEngagement.id).where(
        models.CaregiverEngagement.caregiver_profile_id == profile_id,
        models.CaregiverEngagement.family_user_id == user.id,
        models.CaregiverEngagement.status == "ended",
        models.CaregiverEngagement.review_id.is_(None)).limit(1))).first() is not None
    last_request = (await db.execute(select(models.HireRequest).where(
        models.HireRequest.caregiver_profile_id == profile_id,
        models.HireRequest.family_user_id == user.id)
        .order_by(models.HireRequest.created_at.desc()).limit(1))).scalars().first()
    my_request = None
    if last_request is not None and not my_engagement:
        recent = last_request.responded_at is None or as_utc(last_request.responded_at) > now_utc() - timedelta(days=7)
        if last_request.status in ("pending", "declined", "unavailable") and recent:
            my_request = MyHireRequestOut(request_id=last_request.id, status=last_request.status,
                                          created_at=last_request.created_at)
    conversation = (await db.execute(select(models.ChatConversation.id).where(
        models.ChatConversation.caregiver_profile_id == profile_id,
        models.ChatConversation.family_user_id == user.id))).first()
    return CaregiverPublicOut(
        profile_id=p.id, headline=p.headline, bio=p.bio, years_experience=p.years_experience,
        specialties=p.specialties or [], languages=p.languages or [], zones=p.zones or [],
        certifications=p.certifications or [], rating_avg=p.rating_avg, reviews_count=p.reviews_count,
        is_listed=p.is_listed, is_featured=p.is_featured, full_name=p.user.full_name,
        photo_url=p.user.avatar_url, hired_by_me=my_engagement is not None,
        my_engagement_id=my_engagement.id if my_engagement else None,
        is_engaged=await _is_engaged(db, profile_id), can_review=can_review,
        conversation_id=conversation[0] if conversation else None, my_request=my_request,
        reviews=[ReviewOut(review_id=r.id, rating=r.rating, comment=r.comment,
                          author_name=r.author_name, created_at=r.created_at) for r in reviews])


# ---------- Solicitar la contratación de una cuidadora ----------
# La familia envía una solicitud; el trabajo solo empieza cuando la cuidadora la acepta.
@router.post("/caregivers/{profile_id}/hire-requests", response_model=HireRequestOut, status_code=201)
async def request_hire(profile_id: UUID, body: HireRequestIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede solicitar la contratación de una cuidadora.")
    p = await _get_listed(db, profile_id)
    already = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == profile_id,
        models.CaregiverEngagement.family_user_id == user.id,
        models.CaregiverEngagement.status == "active"))).scalar_one_or_none()
    if already is not None:
        raise conflict("ALREADY_HIRED", "Ya tienes un trabajo activo con esta cuidadora.")
    pending = (await db.execute(select(models.HireRequest).where(
        models.HireRequest.caregiver_profile_id == profile_id,
        models.HireRequest.family_user_id == user.id,
        models.HireRequest.status == "pending"))).scalars().first()
    if pending is not None:
        raise conflict("REQUEST_PENDING", "Ya enviaste una solicitud a esta cuidadora. Espera su respuesta.")
    # Una cuidadora atiende a una familia a la vez: si ya está en servicio no se puede solicitar.
    if await _is_engaged(db, profile_id):
        raise conflict("CAREGIVER_BUSY",
                       "Esta cuidadora ya está trabajando con otra familia. Podrás solicitarla cuando termine ese trabajo.")
    if body.patient_id is not None:
        member = (await db.execute(select(models.PatientMember).where(
            models.PatientMember.patient_id == body.patient_id,
            models.PatientMember.user_id == user.id))).scalar_one_or_none()
        if member is None:
            raise forbidden("No tienes acceso a ese perfil de adulto mayor.")

    text = (body.message or "").strip() or None
    req = models.HireRequest(caregiver_profile_id=profile_id, family_user_id=user.id,
                             patient_id=body.patient_id, message=text)
    db.add(req)
    await db.flush()
    await db.refresh(req)

    # La solicitud abre el chat: así familia y cuidadora pueden conversar antes de decidir.
    await purge_expired(db)
    conv, _ = await get_or_create_conversation(db, p, user)
    intro = "Te envié una solicitud de contratación."
    await add_message(db, conv, user, f"{intro} {text}" if text else intro)
    return HireRequestOut(request_id=req.id, status=req.status, created_at=req.created_at,
                          conversation_id=conv.id)


@router.post("/hire-requests/{request_id}/cancel", status_code=204)
async def cancel_hire_request(request_id: UUID, db: Db, user: CurrentUser):
    r = await db.get(models.HireRequest, request_id)
    if r is None or r.family_user_id != user.id:
        raise not_found()
    if r.status != "pending":
        raise conflict("REQUEST_NOT_PENDING", "Esta solicitud ya fue respondida.")
    r.status = "cancelled"
    r.responded_at = now_utc()


# ---------- Finalizar el trabajo con una cuidadora ----------
@router.post("/engagements/{engagement_id}/end", status_code=204)
async def end_engagement(engagement_id: UUID, db: Db, user: CurrentUser):
    e = await db.get(models.CaregiverEngagement, engagement_id)
    if e is None or e.family_user_id != user.id:
        raise not_found()
    if e.status == "active":
        e.status = "ended"
        e.ended_at = now_utc()
        p = await db.get(models.CaregiverProfile, e.caregiver_profile_id)
        await sync_caregiver_to_admin(p, p.user, await _is_engaged(db, p.id))


# ---------- 14.3 Contactar cuidadora (abre un chat dentro de la aplicación) ----------
@router.post("/caregivers/{profile_id}/contact", response_model=ContactOut, status_code=201)
async def contact_caregiver(profile_id: UUID, body: ContactIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede contactar a una cuidadora.")
    p = await _get_listed(db, profile_id)
    await purge_expired(db)
    conv, created = await get_or_create_conversation(db, p, user)
    text = (body.message or "").strip() or "Hola, vi tu perfil en AgeCare y me gustaría conversar."
    await add_message(db, conv, user, text)
    if created:  # queda además en "Mensajes recibidos" de la cuidadora (se limpia a los 7 días)
        db.add(models.ContactRequest(caregiver_profile_id=profile_id, family_user_id=user.id,
                                     message=text[:500]))
    contact_value = p.user.phone or p.user.email
    channel = "phone" if p.user.phone else "email"
    return ContactOut(contact_channel=channel, contact_value=contact_value, conversation_id=conv.id)


# ---------- 14.4 Calificar cuidadora ----------
# Solo se puede reseñar un trabajo terminado (y una sola vez por trabajo).
@router.post("/caregivers/{profile_id}/reviews", response_model=ReviewCreateOut, status_code=201)
async def review_caregiver(profile_id: UUID, body: ReviewCreateIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede dejar una reseña.")
    p = await _get_listed(db, profile_id)
    engagement = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == profile_id,
        models.CaregiverEngagement.family_user_id == user.id,
        models.CaregiverEngagement.status == "ended",
        models.CaregiverEngagement.review_id.is_(None))
        .order_by(models.CaregiverEngagement.ended_at.desc()))).scalars().first()
    if engagement is None:
        raise conflict("REVIEW_NOT_ALLOWED",
                       "Solo puedes dejar una reseña cuando el trabajo con la cuidadora haya terminado.")

    patient_id = body.patient_id or engagement.patient_id
    display_name = await _family_display_name(db, user, patient_id)
    review = models.CaregiverReview(caregiver_profile_id=profile_id, author_user_id=user.id,
                                    author_name=display_name, rating=body.rating, comment=body.comment)
    db.add(review)
    await db.flush()
    engagement.review_id = review.id

    agg = (await db.execute(select(func.avg(models.CaregiverReview.rating),
                                   func.count(models.CaregiverReview.id))
                            .where(models.CaregiverReview.caregiver_profile_id == profile_id))).one()
    p.rating_avg = round(float(agg[0]), 2)
    p.reviews_count = int(agg[1])
    await sync_review_to_admin(p.user.email, display_name, body.rating, body.comment)
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
