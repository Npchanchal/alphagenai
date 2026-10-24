from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os

from app.api.analyst_routes import router as analyst_router
from app.api.connector_routes import router as connector_router
from app.api.ninja_routes import router as ninja_router
from app.api.routes import router
from app.services.guest_lock import GuestWriteMiddleware
from app.services.rate_limit import RateLimitMiddleware
from app.services.security_headers import SecurityHeadersMiddleware
from app.version import APP_VERSION

app = FastAPI(
    title="CiteAlpha GCI API",
    description="Guidance Credibility Index — management promises vs delivery",
    version=APP_VERSION,
)

_CORS_DEFAULT = (
    "https://citealpha.com,https://www.citealpha.com,"
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5173,http://127.0.0.1:5173"
)
_cors_origins = [
    o.strip()
    for o in os.environ.get("INTELLENS_CORS_ORIGINS", _CORS_DEFAULT).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GuestWriteMiddleware)

app.include_router(router)
app.include_router(analyst_router)
app.include_router(connector_router)
app.include_router(ninja_router)

# Public contract only (W8.5). Workbench, auth, billing, and ops routes stay
# callable; they are omitted from /openapi.json so the published spec is the
# index a licensee integrates against.
_PUBLIC_OPENAPI_PATHS = frozenset(
    {
        "/health",
        "/api/status",
        "/api/meta",
        "/api/trust",
        "/api/compliance/sebi-note",
        "/api/legal/terms",
        "/api/legal/privacy",
        "/api/legal/meta",
        "/api/v1/companies",
        "/api/v1/companies/{company_id}/gci",
        "/api/v1/companies/{company_id}/gci/history",
        "/api/v1/rankings",
        "/api/public/gci-rankings",
        "/api/public/seo-dossiers",
        "/api/v1/index/ledger",
        "/api/v1/index/changelog",
        "/api/v1/index/changelog.rss",
        "/api/v1/index/files",
        "/api/v1/index/files/{name}",
        "/api/v1/index/digest",
        "/api/badge/{ticker}",
        "/api/badge/{ticker}/svg",
        "/api/og/{company_id}.png",
        "/api/og/{company_id}.svg",
        "/api/alerts",
        "/api/metrics",
        "/api/metrics/{metric_id}",
        "/api/sectors/leaderboard",
        "/api/pilot-request",
        "/api/feedback",
        "/api/v1/pit/contract",
        "/api/activity/cite-copy",
    }
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=(
            "Public Guidance Credibility Index reads. "
            "Auth, billing, labeling, and ops routes are not in this spec."
        ),
        routes=app.routes,
    )
    paths = schema.get("paths") or {}
    schema["paths"] = {p: v for p, v in paths.items() if p in _PUBLIC_OPENAPI_PATHS}
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.on_event("startup")
def _start_guidance_review() -> None:
    import os
    import threading

    flag = os.environ.get("INTELLENS_GUIDANCE_REVIEW", "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return
    from app.jobs.guidance_review import serve

    threading.Thread(target=serve, name="guidance-review", daemon=True).start()


@app.on_event("startup")
def _restore_missing_orgs() -> None:
    from app.db.auth_db import use_db_auth

    if use_db_auth():
        from app.services import orgs

        orgs.restore_missing_orgs()


@app.on_event("startup")
def _ensure_protected_users() -> None:
    import logging
    import os

    if os.environ.get("CITEALPHA_PROTECTED_USERS", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    from app.services.protected_users import ensure_protected_users

    try:
        res = ensure_protected_users()
        logging.getLogger(__name__).info(
            "protected_users created=%d repaired=%d skipped=%d",
            len(res["created"]), len(res["repaired"]), len(res["skipped"]),
        )
    except Exception as exc:  # noqa: BLE001 — a bad manifest must not stop the API
        logging.getLogger(__name__).error("protected_users_failed err=%s", type(exc).__name__)
