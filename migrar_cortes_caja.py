"""
Migración: crea la tabla 'cortes_caja'.
"""

from sqlalchemy import inspect
from app.database.connection import engine


def migrar():
    print("Migrando: tabla cortes_caja...")
    inspector = inspect(engine)

    if "cortes_caja" in inspector.get_table_names():
        print("  ⊙ Tabla ya existe")
        return

    from app.database.models import CorteCaja
    CorteCaja.__table__.create(engine)
    print("  ✓ Tabla 'cortes_caja' creada")
    print("\n✅ Migración completada")


if __name__ == "__main__":
    migrar()