import datetime as dt
import secrets
import string
from typing import Union, Optional

from fastapi import status, HTTPException, Depends, Body, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from auth.config import PasswordEncryption, TokenType, JWT
from auth.repositories import ResetCodeRepository
from auth.schemas import TokenOut
from constants import RESET_PASSWORD_EMAIL_SUBJECT, RESET_PASSWORD_EMAIL_MESSAGE
from settings import settings
from users.dependencies import get_user_repo
from users.models import User
from users.repositories import UserRepo
from utils import send_mail

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
            detail='Could not validate credentials.'
        )
    return user


async def get_token_response(user_id: Union[int, str]) -> TokenOut:
    access_token = await JWT.encode_jwt(
        data={'sub': str(user_id), },
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
        if not user.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Account not verified yet. Please wait until a moderator confirms your registration.'
            )
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Incorrect email or password.'
    )


async def login(
        email: str = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        user: User = Depends(authenticate)
) -> TokenOut:
    token_response = await get_token_response(user.id)
    return token_response


async def change_password_service(
        old_password: str,
        new_password: str,
        current_user: User,
        user_repo: UserRepo = Depends(get_user_repo),
):
    if not PasswordEncryption.verify_password(old_password, current_user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Incorrect old password.')
    await user_repo.update_user(
        user_id=current_user.id,
        update_data={'password': PasswordEncryption.hash_password(new_password)}
    )


class ResetCodeService:
    def __init__(self, repo: ResetCodeRepository):
        self._repo = repo

    async def get_code(self, user_id: int) -> Optional[str]:
        entry = await self._repo.get(user_id=user_id)
        if not entry:
            return None
        if dt.datetime.now(dt.UTC) > entry.expiration:
            await self._repo.delete(entry.id)
            return None
        return entry.code

    async def create(self, user_id: int, ttl: int = settings.auth.RESET_PASSWORD_CODE_TTL) -> str:
        expiration = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl)
        alphabet = string.ascii_letters + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(64))
            if (any(c.islower() for c in code)
                    and any(c.isupper() for c in code)
                    and sum(c.isdigit() for c in code) >= 3):
                break
        await self._repo.insert(user_id=user_id, code=code, expiration=expiration)
        return code


async def send_password_reset_code(
        *,
        email: str,
        background_tasks: BackgroundTasks,
        user_repo: UserRepo = Depends(get_user_repo),
        reset_code_service: ResetCodeService,
):
    user = await user_repo.get_by_email(email)
    if not user:
        return

    token = await reset_code_service.create(user_id=user.id)

    reset_link = f'{settings.auth.FRONTEND_RESET_PASSWORD_CALLBACK_URL}?user_id={user.id}&token={token}'

    background_tasks.add_task(
        send_mail,
        to_email=user.email,
        subject=RESET_PASSWORD_EMAIL_SUBJECT,
        message=RESET_PASSWORD_EMAIL_MESSAGE.format(reset_link=reset_link),
    )  # type: ignore


async def receive_password_reset_code(
        *,
        password: str,
        user_id: int,
        token: str,
        user_repo: UserRepo,
        reset_code_service: ResetCodeService,
):
    code = await reset_code_service.get_code(user_id=user_id)
    if code and code != token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid or expired token.'
        )
    await user_repo.update_user(
        user_id=user_id,
        update_data={'password': PasswordEncryption.hash_password(password)}
    )
