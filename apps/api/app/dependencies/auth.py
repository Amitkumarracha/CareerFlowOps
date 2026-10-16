import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.models.entities import Candidate

bearer = HTTPBearer(auto_error=False)


def require_token(expected: str, credentials: HTTPAuthorizationCredentials | None) -> None:
    if not expected:
        raise HTTPException(503, "Access token is not configured")
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            401, "Valid bearer token required", headers={"WWW-Authenticate": "Bearer"}
        )


def admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    require_token(get_settings().admin_api_token, credentials)


def candidate(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> str:
    require_token(get_settings().candidate_api_token, credentials)
    # Single-candidate MVP: identity is server-owned, never supplied through a header.
    if db.get(Candidate, "local-candidate") is None:
        db.add(Candidate(id="local-candidate"))
        db.commit()
    return "local-candidate"
