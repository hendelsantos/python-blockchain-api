"""Ponto de entrada da aplicação FastAPI."""

from fastapi import FastAPI

from blockchain_api import __version__
from blockchain_api.api.routes import router
from blockchain_api.core.blockchain import Blockchain


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

    @application.get("/health", tags=["health"], summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return application


app = create_app()
