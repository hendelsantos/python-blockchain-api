"""Ponto de entrada da aplicação FastAPI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from blockchain_api import __version__
from blockchain_api.api.routes import router
from blockchain_api.core.blockchain import Blockchain

STATIC_DIR = Path(__file__).parent / "static"


def create_app(*, difficulty: int = 3) -> FastAPI:
    application = FastAPI(
        title="Python Blockchain API",
        description="Blockchain educacional com proof-of-work e API REST.",
        version=__version__,
        contact={"name": "Hendel Santos"},
        license_info={"name": "MIT"},
    )
    application.state.blockchain = Blockchain(difficulty=difficulty)
    application.include_router(router)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/health", tags=["health"], summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return application


app = create_app()
