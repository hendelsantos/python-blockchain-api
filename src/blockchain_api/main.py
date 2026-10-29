"""Ponto de entrada da aplicação FastAPI."""

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST

from blockchain_api import __version__
from blockchain_api.api.observability import Observability
from blockchain_api.api.realtime import RealtimeManager
from blockchain_api.api.realtime import router as realtime_router
from blockchain_api.api.routes import router
from blockchain_api.core.blockchain import Blockchain
from blockchain_api.core.network import NodeManager
from blockchain_api.core.repository import BlockchainRepository
from blockchain_api.core.traceability import (
    InMemoryTraceabilityRepository,
    TraceabilityRepository,
    TraceabilityService,
)
from blockchain_api.infrastructure.database import build_repository, build_traceability_repository

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    *,
    difficulty: int = 3,
    repository: BlockchainRepository | None = None,
    node_manager: NodeManager | None = None,
    traceability_repository: TraceabilityRepository | None = None,
) -> FastAPI:
    nodes = node_manager or NodeManager()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await nodes.discover_peers()
        yield

    application = FastAPI(
        title="Python Blockchain API",
        description="Blockchain educacional com proof-of-work e API REST.",
        version=__version__,
        contact={"name": "Hendel Santos"},
        license_info={"name": "MIT"},
        lifespan=lifespan,
    )
    application.state.blockchain = Blockchain(difficulty=difficulty, repository=repository)
    application.state.node_manager = nodes
    application.state.realtime = RealtimeManager()
    application.state.traceability = TraceabilityService(
        traceability_repository or InMemoryTraceabilityRepository()
    )
    application.state.observability = Observability()
    application.include_router(router)
    application.include_router(realtime_router)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.middleware("http")
    async def collect_request_metrics(request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            route = getattr(request.scope.get("route"), "path", request.url.path)
            application.state.observability.record_request(
                method=request.method,
                route=route,
                status=status_code,
                duration=perf_counter() - started_at,
            )
        response.headers["X-Request-ID"] = request_id
        return response

    @application.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/health", tags=["health"], summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        application.state.observability.update_state(
            application.state.blockchain,
            application.state.node_manager,
            application.state.realtime,
        )
        return Response(
            content=application.state.observability.render(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return application


app = create_app(
    repository=build_repository(),
    traceability_repository=build_traceability_repository(),
)
