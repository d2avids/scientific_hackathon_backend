from fastapi import (
    Depends,
    APIRouter,
    Body,
    status,
    BackgroundTasks
)
from pydantic import EmailStr

from auth.config import TokenType, JWT
from auth.openapi import (
    LOGIN_RESPONSES,
    REFRESH_TOKEN_RESPONSES,
    CHANGE_PASSWORD_RESPONSES,
    RESET_PASSWORD_CALLBACK_RESPONSES
)
from auth.schemas import (
    TokenOut,
    RefreshTokenInput,
    ChangePasswordInput,
    NewPasswordInput
)
from auth.services import (
    login,
    get_token_response,
    get_current_user,
    change_password_service,
    reset_password_service,
    reset_password_callback_service
)
from users.dependencies import get_user_repo
from users.models import User
from users.repositories import UserRepo

router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post(
    '/token',
    responses=LOGIN_RESPONSES,
    response_model=TokenOut
)
async def token(
        email: EmailStr = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        token_response: TokenOut = Depends(login),
):
    return token_response


@router.post(
    '/token/refresh',
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


@router.put(
    '/passwords',
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


@router.post(
    '/password-resets',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_password(
        background_tasks: BackgroundTasks,
        email: EmailStr = Body(..., embed=True, title='Email'),
        user_repo: UserRepo = Depends(get_user_repo),
):
    """
    ## Starts the password reset process.

    When a user requests a password reset, an email is sent with a link to reset the password.
    The reset link will be constructed using the frontend URL:

    `{FRONTEND_RESET_PASSWORD_CALLBACK_URL}?user_id=<user_id>&token=<reset_token>`

    Here, `<user_id>` and `<reset_token>` are automatically provided via the email so that
    they can be used on client's side to verify and complete the reset process
    using `/reset-password/set-password` endpoint.
    """
    await reset_password_service(email, background_tasks, user_repo)


@router.post(
    '/password-resets/callback',
    status_code=status.HTTP_204_NO_CONTENT,
    responses=RESET_PASSWORD_CALLBACK_RESPONSES
)
async def reset_password_callback(
        password: NewPasswordInput,
        user_id: int = Body(..., title='User ID from email'),
        token: str = Body(..., title='One-time password reset token from email'),
        user_repo: UserRepo = Depends(get_user_repo),
):
    """
    ## Completes the password reset process by validating the token and updating the user's password.
    """
    await reset_password_callback_service(password.new_password, user_id, token, user_repo)
