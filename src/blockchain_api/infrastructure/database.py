"""Configuração do banco e fábrica do repositório SQLAlchemy."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from blockchain_api.infrastructure.repository import (
    SQLAlchemyBlockchainRepository,
    SQLAlchemyTraceabilityRepository,
)

DEFAULT_DATABASE_URL = "sqlite:///./blockchain.db"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def _alembic_config(database_url: str) -> Config:
    configured_path = os.getenv("ALEMBIC_CONFIG")
    candidates = [
        Path(configured_path) if configured_path else None,
        Path.cwd() / "alembic.ini",
        PROJECT_ROOT / "alembic.ini",
    ]
    config_path = next((path for path in candidates if path and path.exists()), None)
    if config_path is None:
        raise RuntimeError("alembic.ini não foi encontrado")
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def apply_migrations(engine: Engine, database_url: str) -> None:
    """Aplica migrações e reconhece bancos locais criados pela versão 0.3."""

    tables = set(inspect(engine).get_table_names())
    config = _alembic_config(database_url)
    if {"blocks", "pending_transactions"}.issubset(tables) and "alembic_version" not in tables:
        command.stamp(config, "20261028_0001")
    command.upgrade(config, "head")


def build_repository(database_url: str | None = None) -> SQLAlchemyBlockchainRepository:
    resolved_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_database_engine(resolved_url)
    apply_migrations(engine, resolved_url)
    return SQLAlchemyBlockchainRepository(engine)


def build_traceability_repository(
    database_url: str | None = None,
) -> SQLAlchemyTraceabilityRepository:
    resolved_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_database_engine(resolved_url)
    apply_migrations(engine, resolved_url)
    return SQLAlchemyTraceabilityRepository(engine)
