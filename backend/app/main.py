import json
import logging
import secrets
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.api.routes import audit, auth, datasets, sheets, charts, websocket
from app.core.database import SessionLocal
from app.core.request_context import client_ip_from_request
from app.core.security import decode_token

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REQUEST_COUNT = 0
REQUEST_DURATION_SECONDS = 0.0

if settings.DISABLE_AUTH:
    logger.warning(
        "DISABLE_AUTH is enabled: authentication is bypassed and all requests "
        "will be served as the built-in demo user. Do NOT run with this setting "
        "in any environment exposed to untrusted networks."
    )

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A collaborative data exploration and visualization platform",
    docs_url="/docs" if settings.api_docs_enabled() else None,
    redoc_url="/redoc" if settings.api_docs_enabled() else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled() else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _actor_id_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    payload = decode_token(header.split(" ", 1)[1])
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")


def _metrics_token_from_request(request: Request) -> str:
    explicit_token = request.headers.get("x-metrics-token")
    if explicit_token:
        return explicit_token
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return ""


def _ensure_metrics_access(request: Request) -> None:
    if settings.public_metrics_enabled():
        return

    expected_token = settings.METRICS_TOKEN.strip()
    if not expected_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    supplied_token = _metrics_token_from_request(request)
    if not secrets.compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Metrics token required",
        )


@app.middleware("http")
async def structured_request_logging(request: Request, call_next):
    """Emit one safe JSON log per request and keep simple in-process metrics."""
    global REQUEST_COUNT, REQUEST_DURATION_SECONDS

    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - started
        REQUEST_COUNT += 1
        REQUEST_DURATION_SECONDS += duration
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "cf_ray": request.headers.get("cf-ray"),
                    "rndr_id": request.headers.get("rndr-id"),
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "actor_id": _actor_id_from_request(request),
                    "client_host": client_ip_from_request(request),
                }
            )
        )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/health/live")
def liveness_check():
    """Liveness check for process health."""
    return {"status": "alive", "version": settings.VERSION}


@app.get("/health/ready")
def readiness_check():
    """Readiness check for database-backed serving."""
    db = SessionLocal()
    try:
        db.execute(text("select 1"))
    finally:
        db.close()
    return {"status": "ready", "version": settings.VERSION}


@app.get("/metrics")
def metrics(request: Request):
    """Minimal Prometheus-style metrics for public-beta operations."""
    _ensure_metrics_access(request)
    avg_duration = REQUEST_DURATION_SECONDS / REQUEST_COUNT if REQUEST_COUNT else 0
    body = "\n".join(
        [
            "# HELP sigmalite_http_requests_total Total HTTP requests handled.",
            "# TYPE sigmalite_http_requests_total counter",
            f"sigmalite_http_requests_total {REQUEST_COUNT}",
            "# HELP sigmalite_http_request_duration_seconds_sum Total request duration.",
            "# TYPE sigmalite_http_request_duration_seconds_sum counter",
            f"sigmalite_http_request_duration_seconds_sum {REQUEST_DURATION_SECONDS:.6f}",
            "# HELP sigmalite_http_request_duration_seconds_avg Average request duration.",
            "# TYPE sigmalite_http_request_duration_seconds_avg gauge",
            f"sigmalite_http_request_duration_seconds_avg {avg_duration:.6f}",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(datasets.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["Datasets"])
app.include_router(sheets.router, prefix=f"{settings.API_V1_STR}/sheets", tags=["Sheets"])
app.include_router(charts.router, prefix=f"{settings.API_V1_STR}/charts", tags=["Charts"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


if getattr(settings, "ENABLE_OTEL", False):
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:
        logger.warning("OpenTelemetry instrumentation requested but unavailable: %s", exc)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    if settings.DEBUG:
        raise exc
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
