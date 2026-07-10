"""
auth.py — JWT creation and verification.

Uses joserfc — the modern successor to authlib.jose.
Avoids python-jose entirely, eliminating the ecdsa Minerva
attack vulnerability (CVE-2024-23342).
"""

from datetime import datetime, timedelta, timezone
from joserfc import jwt
from joserfc.jwk import OctKey
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from pydantic import BaseModel

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()
key = OctKey.import_key(SECRET_KEY.encode())


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {"sub": username, "exp": int(expire.timestamp())}
    token = jwt.encode({"alg": ALGORITHM}, claims, key)
    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    token = credentials.credentials
    try:
        decoded = jwt.decode(token, key)
        username = decoded.claims.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        # manually check expiry
        exp = decoded.claims.get("exp")
        if exp is None or datetime.now(timezone.utc).timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expired")
        return username
    except HTTPException:
        raise
    except Exception as e:
        print(f"JWT ERROR: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")