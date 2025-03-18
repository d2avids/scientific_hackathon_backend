from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from uvicorn import run

from auth.routers import router as auth_router_v1
from users.routers import router as user_router_v1
from teams.routers import router as team_router_v1
from settings import settings

app = FastAPI(
    debug=settings.DEBUG,
    title=settings.PROJECT_NAME,
    default_response_class=ORJSONResponse,
    redoc_url=settings.REDOC_URL,
    docs_url=settings.DOCS_URL,
    openapi_url=settings.OPENAPI_URL,
)

app.include_router(user_router_v1, prefix='/api/v1', )
app.include_router(auth_router_v1, prefix='/api/v1', )
app.include_router(team_router_v1, prefix='/api/v1', )


if __name__ == '__main__':
    run(
        app='main:app',
        host='127.0.0.1',
        port=8000,
        reload=True,
    )
