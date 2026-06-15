from typing import Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient(settings.oidc_jwks_url)


class CurrentUser(BaseModel):
    subject_id: str
    username: str | None = None
    email: str | None = None
    roles: list[str] = []
    claims: dict[str, Any]


def _extract_roles(claims: dict[str, Any]) -> list[str]:
    realm_roles = claims.get("realm_access", {}).get("roles", [])

    client_roles = (
        claims.get("resource_access", {})
        .get(settings.oidc_client_id, {})
        .get("roles", [])
    )

    return sorted(set(realm_roles + client_roles))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.oidc_algorithm],
            issuer=settings.oidc_issuer,
            options={
                "verify_aud": False,
            },
        )

    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentUser(
        subject_id=claims["sub"],
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        roles=_extract_roles(claims),
        claims=claims,
    )