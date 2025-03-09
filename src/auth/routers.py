from auth.config import TokenType, JWT
from auth.openapi import LOGIN_RESPONSES, REFRESH_TOKEN_RESPONSES, CHANGE_PASSWORD_RESPONSES
from auth.schemas import TokenOut, RefreshTokenInput, ChangePasswordInput
from auth.services import login, get_token_response, get_current_user, change_password_service
from fastapi import Depends, APIRouter, Body, status
from users.dependencies import get_user_repo
from users.models import User
from users.repositories import UserRepo

router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post(
    '/login',
    responses=LOGIN_RESPONSES,
    response_model=TokenOut
)
async def login(
        email: str = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        token_response: TokenOut = Depends(login),
):
    return token_response


@router.post(
    '/refresh',
    responses=REFRESH_TOKEN_RESPONSES,
    response_model=TokenOut
)
async def refresh_token(refresh_token_input: RefreshTokenInput):
    decoded = await JWT.decode_jwt(
        refresh_token_input.refresh_token,
        expected_token_type=TokenType.REFRESH
    )
    token_response = await get_token_response(decoded['sub'])
    return token_response


@router.post(
    '/change-password',
    responses=CHANGE_PASSWORD_RESPONSES,
    status_code=status.HTTP_204_NO_CONTENT
)
async def change_password(
        change_password_input: ChangePasswordInput,
        current_user: User = Depends(get_current_user),
        user_repo: UserRepo = Depends(get_user_repo)
):
    await change_password_service(
        old_password=change_password_input.old_password,
        new_password=change_password_input.new_password,
        current_user=current_user,
        user_repo=user_repo
    )
