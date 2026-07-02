# database/__init__.py
from .database import DatabaseManager, db_manager, get_db
from .models import Base, Historial, Producto

__all__ = [
    "Base",
    "DatabaseManager",
    "Historial",
    "Producto",
    "db_manager",
    "get_db",
]
