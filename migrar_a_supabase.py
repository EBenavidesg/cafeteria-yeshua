"""
Migra la base de datos local (SQLite) a Supabase (PostgreSQL).

1. Crea todas las tablas en Supabase.
2. Copia todos los datos desde cafeteria.db.

Ejecutar UNA SOLA VEZ:
    python migrar_a_supabase.py
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Leer la DIRECT_URL del archivo de secretos ---
def leer_secreto(clave):
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        print("❌ No encontré .streamlit/secrets.toml")
        sys.exit(1)
    for linea in secrets_path.read_text().splitlines():
        linea = linea.strip()
        if linea.startswith(clave):
            # formato: CLAVE = "valor"
            valor = linea.split("=", 1)[1].strip()
            return valor.strip('"').strip("'")
    return None


DIRECT_URL = leer_secreto("DATABASE_URL")
if not DIRECT_URL:
    print("❌ No encontré DIRECT_URL en secrets.toml")
    sys.exit(1)

if DIRECT_URL.startswith("postgres://"):
    DIRECT_URL = DIRECT_URL.replace("postgres://", "postgresql://", 1)
DIRECT_URL = DIRECT_URL.split("?")[0]

print("=" * 60)
print("MIGRACIÓN A SUPABASE")
print("=" * 60)

# --- Conexión a SQLite local (origen) ---
BASE_DIR = Path(__file__).parent
sqlite_engine = create_engine(f"sqlite:///{BASE_DIR / 'cafeteria.db'}")

# --- Conexión a PostgreSQL/Supabase (destino) ---
print("\nConectando a Supabase...")
try:
    pg_engine = create_engine(DIRECT_URL, echo=False)
    # Probar conexión
    with pg_engine.connect() as conn:
        print("✓ Conexión a Supabase exitosa")
except Exception as e:
    print(f"❌ No pude conectar a Supabase: {e}")
    print("\nRevisa que la contraseña en secrets.toml sea correcta.")
    sys.exit(1)

# --- Importar los modelos ---
# Forzamos a que use el engine de Supabase
from app.database.connection import Base
from app.database import models

# --- 1. Crear todas las tablas en Supabase ---
print("\nCreando tablas en Supabase...")
Base.metadata.create_all(pg_engine)
print("✓ Tablas creadas")

# --- 2. Copiar los datos tabla por tabla ---
SqliteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)

# Orden importante: primero las tablas sin dependencias
ORDEN_TABLAS = [
    models.Proveedor,
    models.Empleado,
    models.Insumo,
    models.Producto,
    models.Receta,
    models.Compra,
    models.Venta,
    models.AjusteInventario,
    models.CorteCaja,
]

sqlite_session = SqliteSession()
pg_session = PgSession()

try:
    for modelo in ORDEN_TABLAS:
        nombre_tabla = modelo.__tablename__
        registros = sqlite_session.query(modelo).all()

        if not registros:
            print(f"  ⊙ {nombre_tabla}: vacía, nada que copiar")
            continue

        copiados = 0
        for reg in registros:
            # Copiar todos los campos del registro
            datos = {}
            for columna in modelo.__table__.columns:
                datos[columna.name] = getattr(reg, columna.name)
            nuevo = modelo(**datos)
            pg_session.merge(nuevo)  # merge = inserta o actualiza
            copiados += 1

        pg_session.commit()
        print(f"  ✓ {nombre_tabla}: {copiados} registros copiados")

    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN A SUPABASE COMPLETADA")
    print("=" * 60)

except Exception as e:
    pg_session.rollback()
    print(f"\n❌ ERROR durante la copia: {e}")
    raise
finally:
    sqlite_session.close()
    pg_session.close()