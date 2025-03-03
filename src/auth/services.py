from typing import Union

from auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from auth.config import PasswordEncryption, TokenType, JWT
from auth.schemas import TokenOut

from fastapi import status, HTTPException, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from users.dependencies import get_user_repo
from users.repositories import UserRepo
from users.models import User

security = HTTPBearer()


async def get_current_token_payload(
    auth_header: HTTPAuthorizationCredentials = Depends(security)
):
    token = auth_header.credentials
    decoded = await JWT.decode_jwt(token, expected_token_type=TokenType.ACCESS)
    return decoded


async def get_current_user(
    user_repo: UserRepo = Depends(get_user_repo),
    payload: dict = Depends(get_current_token_payload)
) -> User:
    try:
        user_id: int = int(payload['sub'])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid Token'
        )
    user = await user_repo.get_by_id(user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials'
        )
    return user


async def get_token_response(user_id: Union[int, str]) -> TokenOut:
    access_token = await JWT.encode_jwt(
        data={'sub': str(user_id),},
        token_type=TokenType.ACCESS
    )
    refresh_token = await JWT.encode_jwt(
        data={'sub': str(user_id), },
        token_type=TokenType.REFRESH
    )
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_minutes=REFRESH_TOKEN_EXPIRE_MINUTES
    )


async def authenticate(
        email: str = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        user_repo: UserRepo = Depends(get_user_repo),
) -> User:
    user = await user_repo.get_by_email(email)
    if user and PasswordEncryption.verify_password(password, user.password):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Incorrect email or password'
    )


async def login(
        email: str = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        user: User = Depends(authenticate)
) -> TokenOut:
    token_response = await get_token_response(user.id)
    return token_response
