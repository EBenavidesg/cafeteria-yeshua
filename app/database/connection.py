"""
Configuración de la conexión a la base de datos.
Funciona con SQLite (local) o PostgreSQL (producción/nube).

- Si existe la variable de entorno DATABASE_URL, usa esa (PostgreSQL en la nube).
- Si no, usa el archivo SQLite local.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Intentar leer la URL de la base de datos desde:
# 1. Variable de entorno (cuando está en local)
# 2. Streamlit secrets (cuando está desplegado)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    try:
        import streamlit as st
        DATABASE_URL = st.secrets.get("DATABASE_URL", None)
    except Exception:
        DATABASE_URL = None

if DATABASE_URL:
    # --- Modo producción: PostgreSQL en la nube ---
    # Supabase a veces da la URL con 'postgres://', SQLAlchemy necesita 'postgresql://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    # --- Modo local: SQLite ---
    BASE_DIR = Path(__file__).parent.parent.parent
    DB_PATH = BASE_DIR / "cafeteria.db"
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_session():
    """Devuelve una nueva sesión para hablar con la base de datos."""
    return SessionLocal()