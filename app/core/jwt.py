import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

SECRET_KEY = settings.JWT_SECRET  # use env var in production
ALGORITHM = settings.JWT_ALGO
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
