"""
MongoDB database seeding system.
Creates sample data for products, customers, orders, and inventory.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker
import random
from src.database.mongodb import mongodb_client
from src.models.mongodb_models import Product, Customer, Order, OrderItem, Inventory
from src.config import settings
import logging

logger = logging.getLogger(__name__)
fake = Faker()


class MongoDBSeeder:
    """Handles seeding MongoDB with sample e-commerce data"""
    
    def __init__(self):
        self.products = []
        self.customers = []
        self.categories = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports"]
        
    async def seed_all(self) -> bool:
        """Seed all collections with sample data"""
        try:
            if not mongodb_client.is_connected:
                await mongodb_client.connect()
            
            db = mongodb_client.database
            
            # Check if data already exists
            product_count = await db.products.count_documents({})
            if product_count > 0:
                logger.info(f"Database already contains {product_count} products, skipping seeding")
                return True
            
            logger.info("Starting MongoDB database seeding...")
            
            # Seed in order (products first, then customers, then orders, then inventory)
            await self._seed_products(db)
            await self._seed_customers(db)
            await self._seed_orders(db)
            await self._seed_inventory(db)
            
            logger.info("✅ MongoDB database seeding completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database seeding failed: {e}", exc_info=True)
            return False
    
    async def _seed_products(self, db) -> None:
        """Seed products collection"""
        logger.info("Seeding products...")
        
        product_templates = [
            # Electronics
            {"name": "MacBook Pro", "category": "Electronics", "price_range": (999, 2499), "brand": "Apple"},
            {"name": "iPhone", "category": "Electronics", "price_range": (699, 1199), "brand": "Apple"},
            {"name": "Samsung Galaxy", "category": "Electronics", "price_range": (599, 1099), "brand": "Samsung"},
            {"name": "Dell XPS Laptop", "category": "Electronics", "price_range": (899, 1899), "brand": "Dell"},
            {"name": "Sony Headphones", "category": "Electronics", "price_range": (99, 399), "brand": "Sony"},
            
            # Clothing
            {"name": "T-Shirt", "category": "Clothing", "price_range": (19, 49), "brand": "Various"},
            {"name": "Jeans", "category": "Clothing", "price_range": (39, 129), "brand": "Levi's"},
            {"name": "Sneakers", "category": "Clothing", "price_range": (59, 199), "brand": "Nike"},
            {"name": "Hoodie", "category": "Clothing", "price_range": (29, 89), "brand": "Adidas"},
            {"name": "Dress Shirt", "category": "Clothing", "price_range": (35, 95), "brand": "Various"},
            
            # Books
            {"name": "Python Programming", "category": "Books", "price_range": (29, 69), "brand": "O'Reilly"},
            {"name": "Data Science Guide", "category": "Books", "price_range": (39, 79), "brand": "Packt"},
            {"name": "Web Development", "category": "Books", "price_range": (25, 59), "brand": "Manning"},
            
            # Home & Garden
            {"name": "Coffee Maker", "category": "Home & Garden", "price_range": (49, 299), "brand": "Keurig"},
            {"name": "Plant Pot", "category": "Home & Garden", "price_range": (15, 89), "brand": "Various"},
            {"name": "LED Light Bulb", "category": "Home & Garden", "price_range": (9, 29), "brand": "Philips"},
            
            # Sports
            {"name": "Yoga Mat", "category": "Sports", "price_range": (19, 69), "brand": "Manduka"},
            {"name": "Dumbbells", "category": "Sports", "price_range": (29, 199), "brand": "Bowflex"},
            {"name": "Basketball", "category": "Sports", "price_range": (19, 59), "brand": "Spalding"}
        ]
        
        products_to_insert = []
        
        for i in range(settings.MOCK_PRODUCT_COUNT):
            template = random.choice(product_templates)
            
            # Generate variations
            color_variants = ["Red", "Blue", "Black", "White", "Green", ""]
            size_variants = ["Small", "Medium", "Large", "XL", ""]
            
            color = random.choice(color_variants)
            size = random.choice(size_variants)
            
            # Create product name with variants
            name_parts = [color, template["name"], size]
            name = " ".join([part for part in name_parts if part]).strip()
            
            product = Product(
                name=name,
                category=template["category"],
                price=round(random.uniform(*template["price_range"]), 2),
                description=fake.text(max_nb_chars=200),
                sku=f"{template['brand'][:3].upper()}-{str(uuid.uuid4())[:8].upper()}",
                brand=template["brand"],
                weight=round(random.uniform(0.1, 5.0), 2),
                dimensions=f"{random.randint(5, 50)}x{random.randint(5, 50)}x{random.randint(5, 20)} cm"
            )
            
            products_to_insert.append(product.dict(by_alias=True))
            self.products.append(product)
        
        await db.products.insert_many(products_to_insert)
        logger.info(f"✅ Seeded {len(products_to_insert)} products")
    
    async def _seed_customers(self, db) -> None:
        """Seed customers collection"""
        logger.info("Seeding customers...")
        
        customers_to_insert = []
        
        for i in range(settings.MOCK_USER_COUNT):
            customer = Customer(
                name=fake.name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                address=fake.address(),
                city=fake.city(),
                country=fake.country(),
                loyalty_tier=random.choice(["Bronze", "Silver", "Gold", "Platinum"])
            )
            
            customers_to_insert.append(customer.dict(by_alias=True))
            self.customers.append(customer)
        
        await db.customers.insert_many(customers_to_insert)
        logger.info(f"✅ Seeded {len(customers_to_insert)} customers")
    
    async def _seed_orders(self, db) -> None:
        """Seed orders collection"""
        logger.info("Seeding orders...")
        
        orders_to_insert = []
        
        # Update customers with order data
        customer_updates = {}
        
        for i in range(settings.MOCK_ORDER_COUNT):
            customer = random.choice(self.customers)
            
            # Create order items
            num_items = random.randint(1, 5)
            items = []
            total_amount = 0
            
            for _ in range(num_items):
                product = random.choice(self.products)
                quantity = random.randint(1, 3)
                unit_price = product.price
                discount = round(random.uniform(0, unit_price * 0.2), 2) if random.random() < 0.3 else 0
                total_price = (unit_price * quantity) - discount
                
                item = OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount=discount,
                    total_price=total_price
                )
                items.append(item)
                total_amount += total_price
            
            # Add shipping cost
            shipping_cost = round(random.uniform(5, 25), 2)
            total_amount += shipping_cost
            
            # Create order
            order_date = fake.date_time_between(start_date='-1y', end_date='now')
            
            order = Order(
                customer_id=customer.customer_id,
                customer_name=customer.name,
                customer_email=customer.email,
                order_date=order_date,
                status=random.choice(["pending", "processing", "shipped", "completed", "cancelled"]),
                total_amount=round(total_amount, 2),
                shipping_address=customer.address,
                payment_method=random.choice(["credit_card", "debit_card", "paypal", "bank_transfer"]),
                shipping_cost=shipping_cost,
                items=[item.dict() for item in items]
            )
            
            orders_to_insert.append(order.dict(by_alias=True))
            
            # Track customer statistics
            if customer.customer_id not in customer_updates:
                customer_updates[customer.customer_id] = {
                    "total_orders": 0,
                    "total_spent": 0.0,
                    "last_purchase_date": order_date
                }
            
            customer_updates[customer.customer_id]["total_orders"] += 1
            customer_updates[customer.customer_id]["total_spent"] += total_amount
            if order_date > customer_updates[customer.customer_id]["last_purchase_date"]:
                customer_updates[customer.customer_id]["last_purchase_date"] = order_date
        
        await db.orders.insert_many(orders_to_insert)
        
        # Update customer statistics
        for customer_id, stats in customer_updates.items():
            await db.customers.update_one(
                {"customer_id": customer_id},
                {
                    "$set": {
                        "total_orders": stats["total_orders"],
                        "total_spent": round(stats["total_spent"], 2),
                        "last_purchase_date": stats["last_purchase_date"]
                    }
                }
            )
        
        logger.info(f"✅ Seeded {len(orders_to_insert)} orders and updated customer statistics")
    
    async def _seed_inventory(self, db) -> None:
        """Seed inventory collection"""
        logger.info("Seeding inventory...")
        
        inventory_to_insert = []
        
        for product in self.products:
            inventory = Inventory(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=random.randint(0, 500),
                reserved_quantity=random.randint(0, 20),
                reorder_level=random.randint(5, 50),
                max_stock_level=random.randint(100, 1000),
                low_stock_threshold=random.randint(5, 20),
                supplier=fake.company(),
                cost_per_unit=round(product.price * random.uniform(0.4, 0.7), 2)
            )
            
            # Calculate available quantity
            inventory.available_quantity = max(0, inventory.quantity - inventory.reserved_quantity)
            
            inventory_to_insert.append(inventory.dict(by_alias=True))
        
        await db.inventory.insert_many(inventory_to_insert)
        logger.info(f"✅ Seeded {len(inventory_to_insert)} inventory items")
    
    async def clear_all_data(self) -> bool:
        """Clear all seeded data - useful for re-seeding"""
        try:
            if not mongodb_client.is_connected:
                await mongodb_client.connect()
            
            db = mongodb_client.database
            
            logger.info("Clearing all collections...")
            
            await db.products.delete_many({})
            await db.customers.delete_many({})
            await db.orders.delete_many({})
            await db.inventory.delete_many({})
            
            logger.info("✅ All collections cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear data: {e}", exc_info=True)
            return False


# Global seeder instance
mongodb_seeder = MongoDBSeeder()