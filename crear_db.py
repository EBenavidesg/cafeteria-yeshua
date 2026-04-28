"""
Script para crear la base de datos por primera vez.
Ejecutar una sola vez:
    python crear_db.py
"""

from app.database.connection import engine, Base
from app.database import models


def crear_tablas():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")
    print(f"Base de datos en: {engine.url}")


if __name__ == "__main__":
    crear_tablas()