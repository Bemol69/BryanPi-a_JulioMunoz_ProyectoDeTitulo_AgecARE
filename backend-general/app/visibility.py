"""Cuándo un perfil de cuidadora se muestra a las familias y cuándo es "Destacada"."""
from app.security import as_utc, now_utc


def is_publicly_visible(profile) -> bool:
    """Visible = la cuidadora lo dejó público, el staff lo aprobó y no venció su exención de pago."""
    if not profile.is_listed or profile.admin_status != "approved":
        return False
    until = as_utc(profile.listing_until)
    return until is None or until > now_utc()


# "Destacada": reconocimiento automático a la calidad. Se calcula con los datos de hoy (no se guarda), así
# nunca queda desactualizado: si baja su valoración o deja de estar calificada, la pierde sola.
FEATURED_MIN_RATING = 4.5
FEATURED_MIN_REVIEWS = 3


def is_featured(profile) -> bool:
    """Destacada = perfil calificado (pagó su verificación) + valoración alta + reseñas suficientes."""
    return (bool(profile.is_qualified)
            and (profile.rating_avg or 0) >= FEATURED_MIN_RATING
            and (profile.reviews_count or 0) >= FEATURED_MIN_REVIEWS)
