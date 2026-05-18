from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_internal_service_token(
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
) -> None:
    if not settings.internal_service_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal API is not configured (INTERNAL_SERVICE_TOKEN missing)")
    if x_service_token != settings.internal_service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing service token")
