from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.routes import (
    auth,
    tts,
    dashboard,
    hard_items,
    imports,
    languages,
    study_items,
    study_sessions,
    user_settings,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

app = FastAPI(
    title="Vocab API",
    version="0.2.0",
    docs_url="/api/docs" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS only needed for browser clients (web companion / Flutter web).
# DEBUG mode: allow any localhost port so `flutter run -d chrome` just works.
# Production: strict whitelist from CORS_ORIGINS.
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(languages.router, prefix=API_PREFIX)
app.include_router(study_items.router, prefix=API_PREFIX)
app.include_router(study_sessions.router, prefix=API_PREFIX)
app.include_router(hard_items.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(imports.router, prefix=API_PREFIX)
app.include_router(user_settings.router, prefix=API_PREFIX)
app.include_router(tts.router, prefix=API_PREFIX)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
