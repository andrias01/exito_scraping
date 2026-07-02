"""
Gestión de la conexión a SQLite mediante SQLAlchemy.
Provee session factory y utilidades de inicialización.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import Base

logger = logging.getLogger(__name__)


def _enable_wal_mode(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    """Activa WAL mode para mejor concurrencia en SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class DatabaseManager:
    """
    Gestor de la base de datos.
    Implementa el patrón Singleton para la conexión.
    """

    _instance: "DatabaseManager | None" = None
    _engine: Engine | None = None
    _session_factory: sessionmaker | None = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> None:
        """Inicializa el engine y crea todas las tablas."""
        if self._engine is not None:
            return  # Ya inicializado

        settings = get_settings()
        logger.info("Inicializando base de datos: %s", settings.database_url)

        self._engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Registrar el evento para WAL mode y foreign keys
        event.listen(self._engine, "connect", _enable_wal_mode)

        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        Base.metadata.create_all(self._engine)
        logger.info("Base de datos inicializada correctamente.")

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self.initialize()
        assert self._engine is not None
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            self.initialize()
        assert self._session_factory is not None
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager que provee una sesión con manejo de errores."""
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def drop_all(self) -> None:
        """Elimina todas las tablas. Usar solo en tests."""
        Base.metadata.drop_all(self.engine)


# Instancia global
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI para inyectar sesiones de base de datos.
    Uso: session: Session = Depends(get_db)
    """
    with db_manager.get_session() as session:
        yield session
