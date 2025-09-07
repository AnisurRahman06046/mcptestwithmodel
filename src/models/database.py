from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)
    sku = Column(String(100), unique=True)
    brand = Column(String(100))
    weight = Column(Float)
    dimensions = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    loyalty_tier = Column(String(20), default="Bronze")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_purchase_date = Column(DateTime)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="pending")
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(Text)
    payment_method = Column(String(50))
    discount_applied = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    notes = Column(Text)
    fulfilled_date = Column(DateTime)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Inventory(Base):
    __tablename__ = "inventory"
    
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    max_stock_level = Column(Integer, default=1000)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    supplier = Column(String(255))
    cost_per_unit = Column(Float)
    
    # Relationships
    product = relationship("Product", back_populates="inventory")