"""Dashboard de métricas de marketing y fidelización."""
from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app import models
from app.deps import Db, require
from app.enums import CaregiverStatus
from app.schemas.marketing import MarketingDashboardOut, TopCaregiverOut
from app.security import now_utc

router = APIRouter(prefix="/marketing", tags=["Marketing y fidelización"])


@router.get("/dashboard/summary", response_model=MarketingDashboardOut,
           dependencies=[require("marketing")])
async def dashboard_summary(db: Db, days: int = 30):
    since = now_utc() - timedelta(days=days)

    active_caregivers = (await db.execute(
        select(func.count()).select_from(models.CaregiverProfile)
        .where(models.CaregiverProfile.status == CaregiverStatus.approved))).scalar_one()
    pending_caregivers = (await db.execute(
        select(func.count()).select_from(models.CaregiverProfile)
        .where(models.CaregiverProfile.status == CaregiverStatus.pending))).scalar_one()

    avg_rating = (await db.execute(
        select(func.avg(models.CaregiverProfile.rating_avg))
        .where(models.CaregiverProfile.status == CaregiverStatus.approved))).scalar_one()

    points_sub = (select(models.CaregiverPointsLog.caregiver_id,
                         func.sum(models.CaregiverPointsLog.points).label("points"))
                 .group_by(models.CaregiverPointsLog.caregiver_id).subquery())

    avg_points = (await db.execute(
        select(func.coalesce(func.avg(points_sub.c.points), 0))
        .select_from(models.CaregiverProfile)
        .outerjoin(points_sub, points_sub.c.caregiver_id == models.CaregiverProfile.id)
        .where(models.CaregiverProfile.status == CaregiverStatus.approved))).scalar_one()

    reviews_last = (await db.execute(
        select(func.count()).select_from(models.CaregiverReview)
        .where(models.CaregiverReview.created_at >= since))).scalar_one()
    points_last = (await db.execute(
        select(func.coalesce(func.sum(models.CaregiverPointsLog.points), 0))
        .where(models.CaregiverPointsLog.created_at >= since))).scalar_one()

    top_rows = (await db.execute(
        select(models.CaregiverProfile, func.coalesce(points_sub.c.points, 0))
        .outerjoin(points_sub, points_sub.c.caregiver_id == models.CaregiverProfile.id)
        .where(models.CaregiverProfile.status == CaregiverStatus.approved)
        .order_by(func.coalesce(points_sub.c.points, 0).desc())
        .limit(5))).all()

    return MarketingDashboardOut(
        active_caregivers=int(active_caregivers),
        pending_caregivers=int(pending_caregivers),
        avg_points=round(float(avg_points), 1),
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        reviews_last_30d=int(reviews_last),
        points_awarded_last_30d=int(points_last),
        top5=[TopCaregiverOut(caregiver_id=c.id, name=c.name, zone=c.zone, points=int(pts),
                              rating_avg=c.rating_avg) for c, pts in top_rows],
    )
