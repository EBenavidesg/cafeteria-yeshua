"""
Migración: agrega los campos de caja registradora y anulaciones a la tabla ventas.

Ejecutar UNA SOLA VEZ:
    python migrar_caja_y_anulaciones.py

Si ya se ejecutó antes, simplemente reporta que las columnas ya existen.
"""

from sqlalchemy import inspect, text
from app.database.connection import engine, get_session
from app.database.models import Venta


# Columnas nuevas a agregar a 'ventas'
NUEVAS_COLUMNAS = {
    "transaccion_id":   "TEXT",
    "metodo_pago":      "TEXT",
    "monto_recibido":   "REAL",
    "vuelto":           "REAL",
    "anulada":          "BOOLEAN DEFAULT 0",
    "fecha_anulacion":  "DATETIME",
    "motivo_anulacion": "TEXT",
    "anulada_por_id":   "INTEGER REFERENCES empleados(id)",
}


def migrar():
    print("=" * 60)
    print("MIGRACIÓN: caja registradora + anulaciones")
    print("=" * 60)

    inspector = inspect(engine)
    columnas_existentes = [col["name"] for col in inspector.get_columns("ventas")]

    print(f"\nColumnas actuales en 'ventas': {columnas_existentes}")
    print()

    agregadas = 0
    saltadas = 0

    with engine.begin() as conn:
        for nombre_col, tipo_col in NUEVAS_COLUMNAS.items():
            if nombre_col in columnas_existentes:
                print(f"  ⊙ Columna '{nombre_col}' ya existe. Saltando.")
                saltadas += 1
            else:
                sql = f"ALTER TABLE ventas ADD COLUMN {nombre_col} {tipo_col}"
                conn.execute(text(sql))
                print(f"  ✓ Columna '{nombre_col}' agregada ({tipo_col})")
                agregadas += 1

    print(f"\nResumen: {agregadas} columnas agregadas, {saltadas} ya existían")

    # Verificación final
    inspector_final = inspect(engine)
    columnas_finales = [col["name"] for col in inspector_final.get_columns("ventas")]
    print(f"\n✅ Columnas finales en 'ventas':")
    for c in columnas_finales:
        print(f"   - {c}")

    # Probar que se puede consultar la tabla
    session = get_session()
    try:
        total_ventas = session.query(Venta).count()
        print(f"\n✅ Total ventas en BD: {total_ventas} (la tabla funciona correctamente)")
    finally:
        session.close()


if __name__ == "__main__":
    migrar()