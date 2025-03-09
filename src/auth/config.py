from datetime import datetime, timedelta, timezone
from enum import Enum

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
