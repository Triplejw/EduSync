"""Auth utilities: password hashing and JWT-based get_current_user."""
from fastapi import HTTPException, Header

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    import hashlib
    pwd_context = None


def get_password_hash(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a hashed password.
    Uses bcrypt via passlib if available, otherwise falls back to SHA-256.
    """
    if pwd_context:
        return pwd_context.verify(plain, hashed)
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def get_current_user(authorization: str = Header(None, alias="Authorization")):
    """Validate JWT from Authorization: Bearer <token> and return User from DB."""
    if not authorization:
        raise HTTPException(401, "Missing authorization (Authorization: Bearer <token>)")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid authorization format")
    token = parts[1]

    from jwt_utils import decode_access_token
    from database import SessionLocal, User

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(401, "Invalid or expired token")

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(401, "Invalid token")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(401, "User not found")
        return user
    finally:
        db.close()
