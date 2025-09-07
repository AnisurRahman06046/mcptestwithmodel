import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from src.models.database import Product, Customer, Order, OrderItem, Inventory
from src.database.connection import get_db_context
from src.config import settings
import logging

logger = logging.getLogger(__name__)
fake = Faker()

# Predefined categories and products for realistic data
CATEGORIES = {
    "Electronics": [
        {"name": "MacBook Pro 16\"", "price": 2499.99, "brand": "Apple"},
        {"name": "iPhone 15 Pro", "price": 999.99, "brand": "Apple"},
        {"name": "Samsung Galaxy S24", "price": 899.99, "brand": "Samsung"},
        {"name": "Dell XPS 13", "price": 1299.99, "brand": "Dell"},
        {"name": "iPad Air", "price": 599.99, "brand": "Apple"},
        {"name": "AirPods Pro", "price": 249.99, "brand": "Apple"},
        {"name": "Sony WH-1000XM5", "price": 399.99, "brand": "Sony"},
        {"name": "Nintendo Switch", "price": 299.99, "brand": "Nintendo"},
        {"name": "PlayStation 5", "price": 499.99, "brand": "Sony"},
        {"name": "LG OLED TV 55\"", "price": 1499.99, "brand": "LG"}
    ],
    "Clothing": [
        {"name": "Red Cotton T-Shirt", "price": 29.99, "brand": "BasicWear"},
        {"name": "Blue Denim Jeans", "price": 79.99, "brand": "DenimCo"},
        {"name": "Black Leather Jacket", "price": 199.99, "brand": "LeatherLux"},
        {"name": "White Sneakers", "price": 89.99, "brand": "SportStyle"},
        {"name": "Wool Winter Coat", "price": 299.99, "brand": "WarmWear"},
        {"name": "Silk Dress Shirt", "price": 89.99, "brand": "FormalFit"},
        {"name": "Cotton Hoodie", "price": 59.99, "brand": "ComfortCo"},
        {"name": "Running Shorts", "price": 34.99, "brand": "ActiveWear"},
        {"name": "Cashmere Scarf", "price": 79.99, "brand": "LuxuryKnits"},
        {"name": "Canvas Belt", "price": 39.99, "brand": "AccessoryPro"}
    ],
    "Books": [
        {"name": "The Great Gatsby", "price": 14.99, "brand": "ClassicBooks"},
        {"name": "To Kill a Mockingbird", "price": 16.99, "brand": "ClassicBooks"},
        {"name": "1984", "price": 15.99, "brand": "ClassicBooks"},
        {"name": "Pride and Prejudice", "price": 13.99, "brand": "ClassicBooks"},
        {"name": "The Catcher in the Rye", "price": 15.99, "brand": "ClassicBooks"},
        {"name": "Python Programming Guide", "price": 49.99, "brand": "TechBooks"},
        {"name": "Machine Learning Basics", "price": 59.99, "brand": "TechBooks"},
        {"name": "Web Development 101", "price": 39.99, "brand": "TechBooks"},
        {"name": "Data Science Handbook", "price": 69.99, "brand": "TechBooks"},
        {"name": "AI and the Future", "price": 44.99, "brand": "TechBooks"}
    ],
    "Home & Garden": [
        {"name": "Coffee Maker", "price": 79.99, "brand": "BrewMaster"},
        {"name": "Vacuum Cleaner", "price": 199.99, "brand": "CleanPro"},
        {"name": "Air Purifier", "price": 149.99, "brand": "FreshAir"},
        {"name": "Garden Hose", "price": 29.99, "brand": "GardenGear"},
        {"name": "Outdoor Chair Set", "price": 199.99, "brand": "PatioPlus"},
        {"name": "Kitchen Knife Set", "price": 89.99, "brand": "ChefTools"},
        {"name": "Bedding Set Queen", "price": 79.99, "brand": "ComfortHome"},
        {"name": "Table Lamp", "price": 49.99, "brand": "LightUp"},
        {"name": "Throw Pillows", "price": 24.99, "brand": "DecorStyle"},
        {"name": "Wall Mirror", "price": 89.99, "brand": "ReflectCo"}
    ],
    "Sports": [
        {"name": "Basketball", "price": 29.99, "brand": "SportsBall"},
        {"name": "Tennis Racket", "price": 129.99, "brand": "RacketPro"},
        {"name": "Yoga Mat", "price": 39.99, "brand": "FlexFit"},
        {"name": "Dumbbells 20lb", "price": 89.99, "brand": "StrengthGear"},
        {"name": "Running Shoes", "price": 119.99, "brand": "RunFast"},
        {"name": "Bicycle Helmet", "price": 59.99, "brand": "SafeRide"},
        {"name": "Swimming Goggles", "price": 19.99, "brand": "AquaVision"},
        {"name": "Golf Club Set", "price": 399.99, "brand": "GolfPro"},
        {"name": "Fitness Tracker", "price": 199.99, "brand": "HealthTech"},
        {"name": "Resistance Bands", "price": 24.99, "brand": "FlexFit"}
    ]
}

ORDER_STATUSES = ["pending", "processing", "shipped", "fulfilled", "cancelled"]
LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]


def create_products(db: Session) -> list[Product]:
    """Create sample products"""
    products = []
    for category, items in CATEGORIES.items():
        for item in items:
            product = Product(
                name=item["name"],
                category=category,
                price=item["price"],
                description=fake.text(max_nb_chars=200),
                sku=f"{category[:3].upper()}-{fake.uuid4()[:8].upper()}",
                brand=item["brand"],
                weight=round(random.uniform(0.1, 10.0), 2),
                dimensions=f"{random.randint(5, 50)}x{random.randint(5, 50)}x{random.randint(1, 20)}cm"
            )
            db.add(product)
            products.append(product)
    
    db.commit()
    return products


def create_inventory(db: Session, products: list[Product]):
    """Create inventory records for products"""
    for product in products:
        inventory = Inventory(
            product_id=product.id,
            quantity=random.randint(0, 500),
            reserved_quantity=random.randint(0, 50),
            reorder_level=random.randint(5, 20),
            max_stock_level=random.randint(100, 1000),
            supplier=fake.company(),
            cost_per_unit=round(product.price * 0.6, 2)  # 60% of selling price
        )
        db.add(inventory)
    
    db.commit()


def create_customers(db: Session) -> list[Customer]:
    """Create sample customers"""
    customers = []
    for _ in range(settings.MOCK_USER_COUNT):
        customer = Customer(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number(),
            address=fake.address(),
            city=fake.city(),
            country=fake.country(),
            loyalty_tier=random.choice(LOYALTY_TIERS),
            created_at=fake.date_time_between(start_date="-2y", end_date="now")
        )
        db.add(customer)
        customers.append(customer)
    
    db.commit()
    return customers


def create_orders(db: Session, customers: list[Customer], products: list[Product]):
    """Create sample orders with order items"""
    for _ in range(settings.MOCK_ORDER_COUNT):
        customer = random.choice(customers)
        order_date = fake.date_time_between(start_date="-1y", end_date="now")
        
        # Create order
        order = Order(
            customer_id=customer.id,
            order_date=order_date,
            status=random.choice(ORDER_STATUSES),
            shipping_address=fake.address(),
            payment_method=random.choice(PAYMENT_METHODS),
            discount_applied=round(random.uniform(0, 50), 2),
            shipping_cost=round(random.uniform(5, 25), 2),
            notes=fake.sentence() if random.random() > 0.7 else None,
            total_amount=0  # Will be calculated after adding items
        )
        
        # Add fulfilled date if order is fulfilled
        if order.status == "fulfilled":
            order.fulfilled_date = order_date + timedelta(days=random.randint(1, 14))
        
        db.add(order)
        db.flush()  # Get the order ID
        
        # Create order items (1-5 items per order)
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, min(num_items, len(products)))
        total_amount = order.shipping_cost - order.discount_applied
        
        for product in selected_products:
            quantity = random.randint(1, 3)
            unit_price = product.price
            item_discount = round(random.uniform(0, unit_price * 0.1), 2)
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                discount=item_discount
            )
            db.add(order_item)
            total_amount += (unit_price * quantity) - item_discount
        
        order.total_amount = round(total_amount, 2)
    
    db.commit()
    
    # Update customer statistics
    update_customer_stats(db, customers)


def update_customer_stats(db: Session, customers: list[Customer]):
    """Update customer total orders and spending"""
    for customer in customers:
        orders = db.query(Order).filter(Order.customer_id == customer.id).all()
        customer.total_orders = len(orders)
        customer.total_spent = sum(order.total_amount for order in orders if order.status == "fulfilled")
        if orders:
            customer.last_purchase_date = max(order.order_date for order in orders)
    
    db.commit()


def seed_database():
    """Main function to seed the database with sample data"""
    try:
        with get_db_context() as db:
            # Check if data already exists
            if db.query(Product).count() > 0:
                logger.info("Database already contains data, skipping seeding")
                return
            
            logger.info("Starting database seeding...")
            
            # Create products and inventory
            logger.info("Creating products...")
            products = create_products(db)
            logger.info(f"Created {len(products)} products")
            
            logger.info("Creating inventory...")
            create_inventory(db, products)
            logger.info("Inventory created")
            
            # Create customers
            logger.info("Creating customers...")
            customers = create_customers(db)
            logger.info(f"Created {len(customers)} customers")
            
            # Create orders
            logger.info("Creating orders...")
            create_orders(db, customers, products)
            logger.info(f"Created {settings.MOCK_ORDER_COUNT} orders")
            
            logger.info("Database seeding completed successfully")
            
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise


if __name__ == "__main__":
    seed_database()