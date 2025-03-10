import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import jwt
from fastapi import status, HTTPException
from passlib.context import CryptContext
from settings import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

SECRET_KEY = settings.auth.SECRET_KEY
ALGORITHM = settings.auth.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.auth.REFRESH_TOKEN_EXPIRE_MINUTES


class TokenType(str, Enum):
    ACCESS = 'access'
    REFRESH = 'refresh'


class PasswordEncryption:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


class JWT:
    @staticmethod
    async def encode_jwt(data: dict, token_type: TokenType) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES if token_type == TokenType.ACCESS else REFRESH_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update(
            iat=datetime.now(timezone.utc),
            exp=expire,
            type=token_type.value,
        )
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def decode_jwt(token: str, expected_token_type: TokenType):
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=(ALGORITHM,))
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token has expired.'
            )
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token.'
            )
        if decoded.get('type') != expected_token_type.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token. Expected token to be {}.'.format(expected_token_type.value)
            )
        return decoded


class ResetCodeStorage:
    """A storage class for one-time password reset codes with a TTL value."""
    _store = {}

    @classmethod
    def add_code(cls, user_id: str, ttl: int = settings.auth.RESET_PASSWORD_CODE_TTL) -> str:
        expiration = time.time() + ttl
        alphabet = string.ascii_letters + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(64))
            if (any(c.islower() for c in code)
                    and any(c.isupper() for c in code)
                    and sum(c.isdigit() for c in code) >= 3):
                break
        cls._store[user_id] = (code, expiration)
        return code

    @classmethod
    def get_code(cls, user_id: str) -> Optional[str]:
        entry = cls._store.get(user_id)
        if not entry:
            return None
        code, expiration = entry
        if time.time() > expiration:
            cls._store.pop(user_id, None)
            return None
        cls._store.pop(user_id, None)
        return code
