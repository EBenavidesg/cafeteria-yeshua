"""
Migración: agrega empleado_id y proveedor_id a la tabla compras.
"""

from sqlalchemy import inspect, text
from app.database.connection import engine


def migrar():
    print("Migrando tabla 'compras'...")
    inspector = inspect(engine)
    columnas = [c["name"] for c in inspector.get_columns("compras")]
    
    if "empleado_id" in columnas:
        print("  ⊙ Columna 'empleado_id' ya existe")
    else:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE compras ADD COLUMN empleado_id INTEGER REFERENCES empleados(id)"))
        print("  ✓ Columna 'empleado_id' agregada")
    
    if "proveedor_id" in columnas:
        print("  ⊙ Columna 'proveedor_id' ya existe")
    else:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE compras ADD COLUMN proveedor_id INTEGER REFERENCES proveedores(id)"))
        print("  ✓ Columna 'proveedor_id' agregada")

    print("\n✅ Migración completada")


if __name__ == "__main__":
    migrar()