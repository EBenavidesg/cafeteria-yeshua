"""
Migración: agrega el campo 'tipo' a la tabla ventas.
Distingue ventas normales de refrigerios.
"""

from sqlalchemy import inspect, text
from app.database.connection import engine


def migrar():
    print("Migrando tabla 'ventas' (campo tipo)...")
    inspector = inspect(engine)
    columnas = [c["name"] for c in inspector.get_columns("ventas")]

    if "tipo" in columnas:
        print("  ⊙ Columna 'tipo' ya existe")
    else:
        with engine.begin() as conn:
            # Las ventas existentes se marcan como 'VENTA' por defecto
            conn.execute(text("ALTER TABLE ventas ADD COLUMN tipo TEXT DEFAULT 'VENTA'"))
        print("  ✓ Columna 'tipo' agregada (valor por defecto: 'VENTA')")

    print("\n✅ Migración completada")


if __name__ == "__main__":
    migrar()