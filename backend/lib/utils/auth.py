import hashlib
import secrets
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from config import settings

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")

def generate_api_token() -> tuple[str, str]:
    """Returns (token, token_hash)"""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(f"{token}{settings.api_token_salt}".encode()).hexdigest()
    return token, token_hash

def verify_api_token(token: str, token_hash: str) -> bool:
    computed = hashlib.sha256(f"{token}{settings.api_token_salt}".encode()).hexdigest()
    return secrets.compare_digest(computed, token_hash)
