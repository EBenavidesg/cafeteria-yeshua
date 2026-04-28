"""
Configuración de la conexión a la base de datos SQLite.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "cafeteria.db"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    """Devuelve una nueva sesión para hablar con la base de datos."""
    return SessionLocal()