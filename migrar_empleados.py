"""
Migración: agrega la tabla 'empleados' y modifica la tabla 'ventas'
para usar empleado_id.

Ejecutar UNA SOLA VEZ:
    python migrar_empleados.py
"""

from sqlalchemy import inspect, text
from app.database.connection import engine, get_session
from app.database import models
from app.database.models import Empleado


# Lista de empleados a crear
EMPLEADOS_INICIALES = [
    {"nombre": "Emily",   "pin": "7502", "rol": "ADMIN"},
    {"nombre": "Camilo",  "pin": "0606", "rol": "CAJERO"},
    {"nombre": "Elkin",   "pin": "7171", "rol": "CAJERO"},
    {"nombre": "Marissa", "pin": "1514", "rol": "CAJERO"},
]


def migrar():
    print("=" * 60)
    print("MIGRACIÓN: tabla empleados")
    print("=" * 60)

    inspector = inspect(engine)

    # 1. Crear tabla 'empleados' si no existe
    if "empleados" in inspector.get_table_names():
        print("\n✓ La tabla 'empleados' ya existe. Saltando creación.")
    else:
        print("\nCreando tabla 'empleados'...")
        models.Empleado.__table__.create(engine)
        print("✓ Tabla 'empleados' creada.")

    # 2. Agregar columna 'empleado_id' a 'ventas' si no existe
    columnas_ventas = [col["name"] for col in inspector.get_columns("ventas")]

    if "empleado_id" not in columnas_ventas:
        print("\nAgregando columna 'empleado_id' a tabla 'ventas'...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ventas ADD COLUMN empleado_id INTEGER REFERENCES empleados(id)"))
        print("✓ Columna 'empleado_id' agregada.")
    else:
        print("\n✓ La columna 'empleado_id' ya existe en 'ventas'.")

    # 3. Insertar empleados (si no existen)
    print("\n--- Insertando empleados ---")
    session = get_session()
    creados = 0
    existentes = 0

    try:
        for emp_data in EMPLEADOS_INICIALES:
            existente = session.query(Empleado).filter_by(nombre=emp_data["nombre"]).first()
            if existente:
                existentes += 1
                print(f"  ⊙ {emp_data['nombre']} ya existe (PIN no se actualiza)")
            else:
                nuevo = Empleado(
                    nombre=emp_data["nombre"],
                    pin=emp_data["pin"],
                    rol=emp_data["rol"]
                )
                session.add(nuevo)
                creados += 1
                print(f"  ✓ {emp_data['nombre']} ({emp_data['rol']}) - PIN: {emp_data['pin']}")

        session.commit()
        print(f"\n  Resumen: {creados} creados, {existentes} ya existían")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        session.close()

    # 4. Verificar resultado final
    session = get_session()
    try:
        total = session.query(Empleado).count()
        print(f"\n✅ Total empleados en BD: {total}")
        for emp in session.query(Empleado).all():
            print(f"   - {emp.nombre} ({emp.rol})")
    finally:
        session.close()


if __name__ == "__main__":
    migrar()