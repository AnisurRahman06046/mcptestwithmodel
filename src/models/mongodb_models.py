"""
MongoDB document models using Pydantic with UUID primary keys.
Clean, scalable, and database-agnostic approach.
"""

import uuid
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class Product(BaseModel):
    """Product document model for MongoDB."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    sku: str = Field(..., min_length=1, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    weight: Optional[float] = Field(None, gt=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "name": "MacBook Pro",
                "category": "Electronics",
                "price": 1299.99,
                "description": "Apple MacBook Pro with M2 chip",
                "sku": "APPLE-MBP-M2-13",
                "brand": "Apple",
                "weight": 1.4,
                "dimensions": "30.41 x 21.24 x 1.56 cm"
            }
        }


class ProductUpdate(BaseModel):
    """Model for updating a product."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    brand: Optional[str] = Field(None, max_length=100)
    weight: Optional[float] = Field(None, gt=0)
    dimensions: Optional[str] = Field(None, max_length=100)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "MacBook Pro M3",
                "price": 1399.99,
                "description": "Latest Apple MacBook Pro with M3 chip"
            }
        }


class Customer(BaseModel):
    """Customer document model for MongoDB."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    customer_id: str = Field(default_factory=lambda: f"CUST-{str(uuid.uuid4())[:8].upper()}")
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    total_orders: int = Field(default=0, ge=0)
    total_spent: float = Field(default=0.0, ge=0)
    loyalty_tier: str = Field(default="Bronze", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_purchase_date: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "customer_id": "CUST-A1B2C3D4",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "address": "123 Main St",
                "city": "New York",
                "country": "USA",
                "loyalty_tier": "Gold"
            }
        }


class CustomerUpdate(BaseModel):
    """Model for updating a customer."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    loyalty_tier: Optional[str] = Field(None, max_length=20)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Smith",
                "phone": "+1234567891",
                "loyalty_tier": "Platinum"
            }
        }


class OrderItem(BaseModel):
    """Order item subdocument."""
    
    product_id: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1)
    product_sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount: float = Field(default=0.0, ge=0)
    total_price: float = Field(..., gt=0)
    
    class Config:
        schema_extra = {
            "example": {
                "product_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "product_name": "MacBook Pro",
                "product_sku": "APPLE-MBP-M2-13",
                "quantity": 1,
                "unit_price": 1299.99,
                "discount": 0.0,
                "total_price": 1299.99
            }
        }


class Order(BaseModel):
    """Order document model for MongoDB."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    order_id: str = Field(default_factory=lambda: f"ORD-{str(uuid.uuid4())[:8].upper()}")
    customer_id: str = Field(..., min_length=1)
    customer_name: str = Field(..., min_length=1)
    customer_email: EmailStr
    order_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending", max_length=50)
    total_amount: float = Field(..., gt=0)
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    discount_applied: float = Field(default=0.0, ge=0)
    shipping_cost: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None
    fulfilled_date: Optional[datetime] = None
    items: List[OrderItem] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "order_id": "ORD-A1B2C3D4",
                "customer_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com",
                "status": "pending",
                "total_amount": 1399.99,
                "payment_method": "credit_card",
                "shipping_cost": 15.00
            }
        }


class OrderUpdate(BaseModel):
    """Model for updating an order."""
    
    status: Optional[str] = Field(None, max_length=50)
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "shipped",
                "notes": "Expedited shipping requested"
            }
        }


class Inventory(BaseModel):
    """Inventory document model for MongoDB."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    product_id: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1)
    product_sku: str = Field(..., min_length=1)
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    available_quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    max_stock_level: int = Field(default=1000, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    supplier: Optional[str] = Field(None, max_length=255)
    cost_per_unit: Optional[float] = Field(None, gt=0)
    
    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "product_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "product_name": "MacBook Pro",
                "product_sku": "APPLE-MBP-M2-13",
                "quantity": 50,
                "reserved_quantity": 5,
                "available_quantity": 45,
                "reorder_level": 10,
                "supplier": "Apple Inc"
            }
        }


class InventoryUpdate(BaseModel):
    """Model for updating inventory."""

    quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=255)
    cost_per_unit: Optional[float] = Field(None, gt=0)

    class Config:
        schema_extra = {
            "example": {
                "quantity": 75,
                "reorder_level": 15,
                "supplier": "Apple Inc"
            }
        }


class UserSubscription(BaseModel):
    """User subscription model for MongoDB."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str = Field(..., min_length=1)
    shop_id: str = Field(..., min_length=1)

    # Subscription Details
    plan_name: str = Field(..., min_length=1)
    plan_display_name: str = Field(..., min_length=1)
    allocated_tokens: int = Field(..., ge=0)
    monthly_fee: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=3)

    # Status
    status: str = Field(default="active")  # active, suspended, cancelled, expired
    billing_cycle: str = Field(default="monthly")

    # Dates
    subscription_start_date: datetime = Field(default_factory=datetime.utcnow)
    current_period_start: datetime = Field(default_factory=datetime.utcnow)
    current_period_end: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    next_billing_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))

    # History
    plan_history: List[Dict] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="platform")

    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "user_id": "user123",
                "shop_id": "shop456",
                "plan_name": "pro",
                "plan_display_name": "Pro Plan",
                "allocated_tokens": 20000,
                "monthly_fee": 29.99,
                "currency": "USD",
                "status": "active"
            }
        }


class UserTokenUsage(BaseModel):
    """Token usage tracking model for MongoDB."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str = Field(..., min_length=1)
    shop_id: str = Field(..., min_length=1)
    subscription_id: str = Field(..., min_length=1)

    # Usage tracking
    used_tokens: int = Field(default=0, ge=0)
    current_period_start: datetime = Field(default_factory=datetime.utcnow)
    current_period_end: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))

    # Usage breakdown
    daily_usage: List[Dict] = Field(default_factory=list)
    weekly_usage: List[Dict] = Field(default_factory=list)
    monthly_summary: List[Dict] = Field(default_factory=list)

    # Analytics
    total_queries: int = Field(default=0, ge=0)
    avg_tokens_per_query: float = Field(default=0.0)
    peak_daily_usage: int = Field(default=0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "user_id": "user123",
                "shop_id": "shop456",
                "subscription_id": "sub123",
                "used_tokens": 5670,
                "total_queries": 134
            }
        }