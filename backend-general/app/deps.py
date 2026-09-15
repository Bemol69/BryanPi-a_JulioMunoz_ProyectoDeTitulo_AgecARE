"""Dependencia de usuario autenticado."""
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.errors import unauthorized
from app.security import decode_access_token


async def get_current_user(request: Request,
                           db: Annotated[AsyncSession, Depends(get_db)]) -> models.User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise unauthorized()
    try:
        payload = decode_access_token(auth.removeprefix("Bearer ").strip())
    except jwt.PyJWTError:
        raise unauthorized()
    user = await db.get(models.User, UUID(payload["sub"]))
    if user is None:
        raise unauthorized()
    request.state.actor = user
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
Db = Annotated[AsyncSession, Depends(get_db)]


def require_account_type(account_type: str):
    async def checker(user: CurrentUser) -> models.User:
        if user.account_type != account_type:
            from app.errors import forbidden
            raise forbidden(f"Esta acción es solo para cuentas de tipo '{account_type}'.")
        return user
    return Depends(checker)
