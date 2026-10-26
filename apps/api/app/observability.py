import json
import logging
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Info, generate_latest
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from apps.api.app.config import get_settings

HTTP_REQUESTS = Counter(
    "careerflowops_http_requests_total", "HTTP responses", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram("careerflowops_http_duration_seconds", "HTTP request duration", ["route"])
INGESTION_RUNS = Counter(
    "careerflowops_ingestion_runs_total", "Completed ingestion runs", ["status"]
)
JOBS_FETCHED = Counter("careerflowops_jobs_fetched_total", "Fetched source postings", ["source"])
INGESTION_FAILURES = Counter(
    "careerflowops_ingestion_failures_total", "Failed boards or records", ["source"]
)
NORMALIZED = Counter(
    "careerflowops_jobs_normalized_total", "Successfully normalized source postings"
)
DUPLICATES = Counter(
    "careerflowops_duplicates_detected_total", "Additional occurrences assigned to existing jobs"
)
RECOMMENDATIONS = Counter("careerflowops_recommendation_requests_total", "Recommendation requests")
INFERENCE_LATENCY = Histogram("careerflowops_inference_seconds", "Ranking inference duration")
SCORES = Histogram(
    "careerflowops_prediction_score",
    "Returned match scores",
    buckets=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
)
MODEL = Info("careerflowops_model", "Most recently used model identity")
logger = logging.getLogger("careerflowops")


class UploadLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/api/resumes" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        limit = get_settings().max_resume_bytes + 65536
        headers = dict(scope.get("headers", []))
        try:
            too_large = int(headers.get(b"content-length", b"0")) > limit
        except ValueError:
            await JSONResponse({"detail": "Invalid content length"}, 400)(scope, receive, send)
            return
        if too_large:
            await JSONResponse({"detail": "Resume upload is too large"}, 413)(scope, receive, send)
            return
        length = 0

        async def bounded_receive() -> Message:
            nonlocal length
            message = await receive()
            length += len(message.get("body", b""))
            if length > limit:
                raise HTTPException(413, "Resume upload is too large")
            return message

        await self.app(scope, bounded_receive, send)


def instrument(app: FastAPI) -> None:
    logging.basicConfig(level=get_settings().log_level, format="%(message)s")
    app.add_middleware(UploadLimitMiddleware)

    @app.middleware("http")
    async def telemetry(request: Request, call_next) -> Response:
        start = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Content-Type-Options"] = "nosniff"
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            duration = perf_counter() - start
            if get_settings().prometheus_enabled:
                HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
                HTTP_LATENCY.labels(route).observe(duration)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "method": request.method,
                        "route": route,
                        "status": status,
                        "duration_seconds": round(duration, 6),
                    }
                )
            )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Database operation unavailable; please retry."}, status_code=503
        )

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        if not get_settings().prometheus_enabled:
            raise HTTPException(404, "Metrics disabled")
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
