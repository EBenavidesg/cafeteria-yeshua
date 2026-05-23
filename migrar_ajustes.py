"""
Migración: crea la tabla 'ajustes_inventario'.
"""

from sqlalchemy import inspect
from app.database.connection import engine


def migrar():
    print("Migrando: tabla ajustes_inventario...")
    inspector = inspect(engine)
    
    if "ajustes_inventario" in inspector.get_table_names():
        print("  ⊙ Tabla ya existe")
        return
    
    # Importamos después de verificar para que SQLAlchemy lea el modelo nuevo
    from app.database.models import AjusteInventario
    AjusteInventario.__table__.create(engine)
    print("  ✓ Tabla 'ajustes_inventario' creada")
    print("\n✅ Migración completada")


if __name__ == "__main__":
    migrar()