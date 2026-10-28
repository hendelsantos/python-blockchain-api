"""Configuração do banco e fábrica do repositório SQLAlchemy."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from blockchain_api.infrastructure.repository import Base, SQLAlchemyBlockchainRepository

DEFAULT_DATABASE_URL = "sqlite:///./blockchain.db"


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def build_repository(database_url: str | None = None) -> SQLAlchemyBlockchainRepository:
    engine = create_database_engine(database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    Base.metadata.create_all(engine)
    return SQLAlchemyBlockchainRepository(engine)
