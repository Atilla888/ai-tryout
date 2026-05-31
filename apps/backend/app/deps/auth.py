"""Authentication layer.

A single integration point — `get_current_user()` — sits behind an
`AuthProvider` interface so the underlying identity system can be swapped
(Keycloak/OIDC now, Shibboleth later) without touching route code.

Providers turn the incoming `Authorization` header into normalized claims;
`get_current_user` then maps those claims to a row in the `users` table
(just-in-time provisioning) and returns the ORM `User`.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import User
from app.services.users import get_or_create_user_service


@dataclass
class NormalizedClaims:
    """Identity fields every provider must produce, regardless of IdP format."""
    subject_id: str
    email: str
    display_name: str | None = None
    realm_roles: list[str] = field(default_factory=list)


class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, authorization: str | None) -> NormalizedClaims:
        """Validate the Authorization header and return normalized claims, or raise 401."""


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


class OIDCAuthProvider(AuthProvider):
    """Validates Keycloak-issued JWT access tokens against the realm JWKS."""

    def __init__(self) -> None:
        # PyJWKClient fetches the realm's public keys and caches them,
        # refreshing automatically when Keycloak rotates signing keys.
        self._jwks_client = jwt.PyJWKClient(settings.oidc_jwks_url)

    async def authenticate(self, authorization: str | None) -> NormalizedClaims:
        token = _bearer_token(authorization)
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=settings.oidc_issuer,
                audience=settings.oidc_audience if settings.oidc_verify_audience else None,
                options={
                    "verify_aud": settings.oidc_verify_audience,
                    "require": ["exp", "iss", "sub"],
                },
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        return NormalizedClaims(
            subject_id=claims["sub"],
            email=claims.get("email", ""),
            display_name=claims.get("name") or claims.get("preferred_username"),
            realm_roles=claims.get("realm_access", {}).get("roles", []),
        )


class DevAuthProvider(AuthProvider):
    """Local development: no Keycloak needed. Returns a fixed admin user.

    Lets you exercise protected routes from Swagger/tests without a running IdP.
    Never use in production (AUTH_PROVIDER=oidc there).
    """

    async def authenticate(self, authorization: str | None) -> NormalizedClaims:
        return NormalizedClaims(
            subject_id="dev-user",
            email="dev@example.com",
            display_name="Local Dev",
            realm_roles=["admin"],
        )


def _build_provider() -> AuthProvider:
    if settings.auth_provider == "oidc":
        return OIDCAuthProvider()
    return DevAuthProvider()


# One provider instance for the process (JWKS cache lives here).
auth_provider: AuthProvider = _build_provider()


def map_realm_roles_to_role(realm_roles: list[str]) -> str:
    """Collapse Keycloak realm roles into the single platform role we store."""
    if "admin" in realm_roles:
        return "admin"
    if "space_creator" in realm_roles:
        return "space_creator"
    return "end_user"


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    claims = await auth_provider.authenticate(authorization)
    role = map_realm_roles_to_role(claims.realm_roles)
    return await get_or_create_user_service(
        db,
        subject_id=claims.subject_id,
        email=claims.email,
        display_name=claims.display_name,
        role=role,
    )


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    """Dependency factory: allow the route only for the given platform roles."""

    async def _checker(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _checker
