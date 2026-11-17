"""Cuándo un perfil de cuidadora se muestra a las familias."""
from app.security import as_utc, now_utc


def is_publicly_visible(profile) -> bool:
    """Visible = la cuidadora lo dejó público, el staff lo aprobó y no venció su exención de pago."""
    if not profile.is_listed or profile.admin_status != "approved":
        return False
    until = as_utc(profile.listing_until)
    return until is None or until > now_utc()
