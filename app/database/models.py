"""
Modelos de datos del sistema.
Cada clase representa una tabla en la base de datos.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    contacto = Column(String, nullable=True)
    notas = Column(String, nullable=True)

    insumos = relationship("Insumo", back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor {self.nombre}>"


class Insumo(Base):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    unidad = Column(String, nullable=False)
    stock_actual = Column(Float, nullable=False, default=0)
    stock_minimo = Column(Float, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=True)

    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    proveedor = relationship("Proveedor", back_populates="insumos")

    en_recetas = relationship("Receta", back_populates="insumo")
    compras = relationship("Compra", back_populates="insumo")

    def __repr__(self):
        return f"<Insumo {self.nombre}: {self.stock_actual} {self.unidad}>"


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    precio = Column(Float, nullable=False)
    categoria = Column(String, nullable=True)
    activo = Column(Boolean, default=True)

    ingredientes = relationship("Receta", back_populates="producto")
    ventas = relationship("Venta", back_populates="producto")

    def __repr__(self):
        return f"<Producto {self.nombre}: ${self.precio}>"


class Receta(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Float, nullable=False)

    producto = relationship("Producto", back_populates="ingredientes")
    insumo = relationship("Insumo", back_populates="en_recetas")

    def __repr__(self):
        return f"<Receta: {self.producto.nombre} usa {self.cantidad} {self.insumo.nombre}>"


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    costo_total = Column(Float, nullable=True)
    notas = Column(String, nullable=True)

    insumo = relationship("Insumo", back_populates="compras")

    def __repr__(self):
        return f"<Compra {self.fecha.date()}: {self.cantidad} {self.insumo.nombre}>"


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    empleado = Column(String, nullable=True)

    producto = relationship("Producto", back_populates="ventas")

    def __repr__(self):
        return f"<Venta {self.fecha.date()}: {self.cantidad}x {self.producto.nombre}>"