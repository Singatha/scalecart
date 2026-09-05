import logging
import time
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException

from .checks import ReadinessCheck
from .logging import configure_logging, correlation_id_context
from .metrics import HTTP_ERRORS, HTTP_LATENCY, HTTP_REQUESTS

logger = logging.getLogger("scalecart.http")


def _error_response(
    *, status_code: int, code: str, message: str, correlation_id: str, details: Any = None
) -> JSONResponse:
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
        }
    }
    if details is not None:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)


def create_service_app(
    *,
    service_name: str,
    version: str = "0.1.0",
    cors_origins: list[str] | None = None,
    readiness_checks: Mapping[str, ReadinessCheck] | None = None,
    log_level: str = "INFO",
) -> FastAPI:
    configure_logging(log_level)
    app = FastAPI(title=service_name, version=version)
    checks = readiness_checks or {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Response:
        correlation_id = request.headers.get("X-Request-ID") or str(uuid4())
        token = correlation_id_context.set(correlation_id)
        started = time.perf_counter()
        status_code = 500
        path = request.url.path
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = correlation_id
            return response
        finally:
            duration = time.perf_counter() - started
            labels = (service_name, request.method, path, str(status_code))
            HTTP_REQUESTS.labels(*labels).inc()
            HTTP_LATENCY.labels(service_name, request.method, path).observe(duration)
            if status_code >= 400:
                HTTP_ERRORS.labels(*labels).inc()
            logger.info(
                "request_completed",
                extra={
                    "service": service_name,
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            correlation_id_context.reset(token)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = correlation_id_context.get()
        return _error_response(
            status_code=exc.status_code,
            code="http_error",
            message=str(exc.detail),
            correlation_id=correlation_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = correlation_id_context.get()
        return _error_response(
            status_code=422,
            code="validation_error",
            message="The request was invalid.",
            correlation_id=correlation_id,
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = correlation_id_context.get()
        logger.exception("unhandled_exception", extra={"service": service_name})
        return _error_response(
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
            correlation_id=correlation_id,
        )

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": service_name}

    @app.get("/ready", tags=["operations"])
    async def ready() -> JSONResponse:
        results: dict[str, str] = {}
        for name, check in checks.items():
            try:
                await check()
                results[name] = "ready"
            except Exception:
                logger.exception("readiness_check_failed", extra={"service": service_name})
                results[name] = "unavailable"
        is_ready = all(value == "ready" for value in results.values())
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={
                "status": "ready" if is_ready else "not_ready",
                "service": service_name,
                "checks": results,
            },
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
