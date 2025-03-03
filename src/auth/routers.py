from fastapi import Depends, APIRouter, Body

from auth.schemas import TokenOut, RefreshTokenInput
from auth.services import login, get_token_response
from auth.config import TokenType, JWT


router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post('/login', response_model=TokenOut)
async def login(
        email: str = Body(..., title='Email'),
        password: str = Body(..., title='Password'),
        token_response: TokenOut = Depends(login),
):
    return token_response


@router.post('/refresh', response_model=TokenOut)
async def refresh_token(refresh_token_input: RefreshTokenInput):
    decoded = await JWT.decode_jwt(refresh_token_input.refresh_token, expected_token_type=TokenType.REFRESH)
    token_response = await get_token_response(decoded['sub'])
    return token_response
