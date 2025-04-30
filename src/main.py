from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from uvicorn import run

from auth.routers import router as auth_router_v1
from projects.routers import router as project_router_v1
from settings import settings
from teams.routers import router as team_router_v1
from users.routers import router as user_router_v1

app = FastAPI(
    debug=settings.DEBUG,
    title=settings.PROJECT_NAME,
    default_response_class=ORJSONResponse,
    redoc_url=settings.REDOC_URL,
    docs_url=settings.DOCS_URL,
    openapi_url=settings.OPENAPI_URL,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(user_router_v1, prefix='/api/v1', )
app.include_router(auth_router_v1, prefix='/api/v1', )
app.include_router(team_router_v1, prefix='/api/v1', )
app.include_router(project_router_v1, prefix='/api/v1', )

if __name__ == '__main__':
    run(
        app='main:app',
        host='127.0.0.1',
        port=8000,
        reload=True,
    )
