"""Login and identity.

Routes call get_current_user(). Behind that sits an AuthProvider so we can swap
Keycloak for something else later without rewriting every endpoint.

Each provider reads the Authorization header and returns the same claim shape.
get_current_user then finds or creates the matching users row and returns it.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User
from app.services.users import get_or_create_user_service

logger = logging.getLogger(__name__)


@dataclass
class NormalizedClaims:
    """What every identity provider has to give us, no matter how their tokens look."""
    subject_id: str
    email: str
    display_name: str | None = None
    realm_roles: list[str] = field(default_factory=list)


class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, authorization: str | None) -> NormalizedClaims:
        """Check the header and return claims, or raise 401."""


def _bearer_token(authorization: str | None) -> str:
    """Pull the token out of a Bearer header."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


class OIDCAuthProvider(AuthProvider):
    """Check access tokens from Keycloak using the realm public keys."""

    def __init__(self) -> None:
        # PyJWKClient caches keys and refreshes when Keycloak rotates them.
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
    """Local-development fallback used whenever auth_provider is not 'oidc'.

    It ignores the Authorization header entirely and authenticates every request
    as the same admin user, so the app is usable without a running Keycloak.
    This is intentional for local dev only and must never be enabled in
    production — see the startup warning emitted by _build_provider().
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
    logger.warning(
        "DevAuthProvider active - ALL users are treated as admin and the "
        "Authorization header is ignored. Do not use in production "
        "(set auth_provider='oidc')."
    )
    return DevAuthProvider()


auth_provider: AuthProvider = _build_provider()


def map_realm_roles_to_role(realm_roles: list[str]) -> str:
    """Keycloak can send many realm roles; we store one app role per user."""
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
    """Only let through users who have one of the given roles."""

    async def _checker(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _checker
