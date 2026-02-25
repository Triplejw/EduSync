"""JWT creation and validation for EduSync API."""
import os
import secrets
import warnings
from datetime import datetime, timedelta
from typing import Optional

try:
    from jose import jwt
    from jose.exceptions import JWTError
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False

# Secret key: MUST be set via environment variable in production
# If not set, generates a random key (tokens won't persist across restarts)
_env_secret = os.environ.get("EDUSYNC_JWT_SECRET")
if _env_secret:
    SECRET_KEY = _env_secret
else:
    SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn(
        "EDUSYNC_JWT_SECRET not set! Using random secret - tokens will be invalidated on restart. "
        "Set EDUSYNC_JWT_SECRET environment variable for production.",
        RuntimeWarning
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(user_id: int, email: str, role: str) -> str:
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose is not installed. pip install python-jose[cryptography]")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    if not JOSE_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
