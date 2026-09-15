"""Esquemas del dashboard de Marketing y Fidelización (módulo nuevo del equipo)."""
from uuid import UUID

from pydantic import BaseModel


class TopCaregiverOut(BaseModel):
    caregiver_id: UUID
    name: str
    zone: str
    points: int
    rating_avg: float | None


class MarketingDashboardOut(BaseModel):
    active_caregivers: int
    pending_caregivers: int
    avg_points: float
    avg_rating: float | None
    reviews_last_30d: int
    points_awarded_last_30d: int
    top5: list[TopCaregiverOut]
