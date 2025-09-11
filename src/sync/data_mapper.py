"""
Data transformation mapper between MySQL and MongoDB.
Handles data type conversion and field mapping.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

from .mysql_connector import TableInfo
from ..models.mongodb_models import Product, Customer, Order, OrderItem, Inventory

logger = logging.getLogger(__name__)


class DataMapper:
    """
    Transforms MySQL data to MongoDB format with intelligent mapping.
    Handles data type conversion and field normalization.
    """
    
    def __init__(self):
        self.field_mappings = {
            # Common field name mappings from MySQL to MongoDB
            'id': '_id',
            'user_id': 'customer_id',
            'userid': 'customer_id',
            'username': 'name',
            'first_name': 'name',  # Will be combined with last_name
            'email_address': 'email',
            'phone_number': 'phone',
            'created': 'created_at',
            'modified': 'updated_at',
            'date_created': 'created_at',
            'date_modified': 'updated_at',
            'price': 'price',
            'cost': 'price',
            'amount': 'total_amount',
            'qty': 'quantity',
            'stock': 'quantity'
        }
        
        self.type_conversions = {
            'DECIMAL': self._convert_decimal,
            'DATETIME': self._convert_datetime,
            'TIMESTAMP': self._convert_datetime,
            'DATE': self._convert_datetime,
            'TIME': self._convert_time,
            'TINYINT(1)': self._convert_boolean,
            'JSON': self._convert_json,
            'TEXT': self._convert_text,
            'LONGTEXT': self._convert_text
        }
    
    async def transform_table_data(
        self, 
        table_name: str, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Transform MySQL table data to MongoDB format."""
        
        logger.info(f"Transforming {len(mysql_data)} records from table: {table_name}")
        
        # Try to map to specific MongoDB models if available
        if self._is_product_table(table_name, table_info):
            return await self._transform_to_products(mysql_data, table_info)
        elif self._is_customer_table(table_name, table_info):
            return await self._transform_to_customers(mysql_data, table_info)
        elif self._is_order_table(table_name, table_info):
            return await self._transform_to_orders(mysql_data, table_info)
        elif self._is_inventory_table(table_name, table_info):
            return await self._transform_to_inventory(mysql_data, table_info)
        else:
            # Generic transformation
            return await self._transform_generic(mysql_data, table_info)
    
    def _is_product_table(self, table_name: str, table_info: TableInfo) -> bool:
        """Check if table represents products."""
        table_lower = table_name.lower()
        product_indicators = ['product', 'item', 'goods', 'catalog']
        
        if any(indicator in table_lower for indicator in product_indicators):
            return True
        
        # Check for product-like columns
        columns = [col.lower() for col in table_info.columns.keys()]
        product_columns = ['name', 'price', 'sku', 'category']
        return len(set(product_columns) & set(columns)) >= 2
    
    def _is_customer_table(self, table_name: str, table_info: TableInfo) -> bool:
        """Check if table represents customers/users."""
        table_lower = table_name.lower()
        customer_indicators = ['customer', 'user', 'client', 'member', 'account']
        
        if any(indicator in table_lower for indicator in customer_indicators):
            return True
        
        columns = [col.lower() for col in table_info.columns.keys()]
        return 'email' in columns and ('name' in columns or 'first_name' in columns)
    
    def _is_order_table(self, table_name: str, table_info: TableInfo) -> bool:
        """Check if table represents orders."""
        table_lower = table_name.lower()
        order_indicators = ['order', 'purchase', 'transaction', 'sale']
        
        if any(indicator in table_lower for indicator in order_indicators):
            return True
        
        columns = [col.lower() for col in table_info.columns.keys()]
        order_columns = ['customer_id', 'total', 'amount', 'status']
        return len(set(order_columns) & set(columns)) >= 2
    
    def _is_inventory_table(self, table_name: str, table_info: TableInfo) -> bool:
        """Check if table represents inventory."""
        table_lower = table_name.lower()
        inventory_indicators = ['inventory', 'stock', 'warehouse']
        
        if any(indicator in table_lower for indicator in inventory_indicators):
            return True
        
        columns = [col.lower() for col in table_info.columns.keys()]
        inventory_columns = ['product_id', 'quantity', 'stock']
        return len(set(inventory_columns) & set(columns)) >= 2
    
    async def _transform_to_products(
        self, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Transform data to Product model format."""
        
        products = []
        
        for record in mysql_data:
            try:
                # Map common fields
                product_data = {
                    '_id': self._ensure_string_id(record.get('id') or record.get('product_id')),
                    'name': record.get('name') or record.get('product_name') or record.get('title', 'Unknown Product'),
                    'category': record.get('category') or record.get('category_name') or 'Uncategorized',
                    'price': self._convert_to_float(record.get('price') or record.get('cost', 0)),
                    'description': record.get('description') or record.get('details'),
                    'sku': record.get('sku') or record.get('product_code') or f"SKU-{uuid.uuid4().hex[:8].upper()}",
                    'brand': record.get('brand') or record.get('manufacturer'),
                    'weight': self._convert_to_float(record.get('weight')),
                    'dimensions': record.get('dimensions') or record.get('size'),
                    'created_at': self._convert_datetime(record.get('created_at') or record.get('date_created')),
                    'updated_at': self._convert_datetime(record.get('updated_at') or record.get('date_modified'))
                }
                
                # Remove None values
                product_data = {k: v for k, v in product_data.items() if v is not None}
                
                # Ensure required fields
                if not product_data.get('created_at'):
                    product_data['created_at'] = datetime.utcnow()
                if not product_data.get('updated_at'):
                    product_data['updated_at'] = datetime.utcnow()
                
                products.append(product_data)
                
            except Exception as e:
                logger.error(f"Error transforming product record: {e}")
                logger.debug(f"Record: {record}")
        
        return products
    
    async def _transform_to_customers(
        self, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Transform data to Customer model format."""
        
        customers = []
        
        for record in mysql_data:
            try:
                # Handle name field (might be split into first_name, last_name)
                name = record.get('name') or record.get('full_name')
                if not name:
                    first_name = record.get('first_name', '')
                    last_name = record.get('last_name', '')
                    name = f"{first_name} {last_name}".strip() or 'Unknown'
                
                customer_data = {
                    '_id': self._ensure_string_id(record.get('id') or record.get('customer_id') or record.get('user_id')),
                    'customer_id': record.get('customer_id') or f"CUST-{uuid.uuid4().hex[:8].upper()}",
                    'name': name,
                    'email': record.get('email') or record.get('email_address'),
                    'phone': record.get('phone') or record.get('phone_number'),
                    'address': record.get('address') or record.get('street_address'),
                    'city': record.get('city'),
                    'country': record.get('country') or record.get('country_code'),
                    'total_orders': int(record.get('total_orders', 0)),
                    'total_spent': self._convert_to_float(record.get('total_spent', 0.0)),
                    'loyalty_tier': record.get('loyalty_tier') or record.get('tier', 'Bronze'),
                    'created_at': self._convert_datetime(record.get('created_at') or record.get('date_created')),
                    'last_purchase_date': self._convert_datetime(record.get('last_purchase_date'))
                }
                
                # Remove None values
                customer_data = {k: v for k, v in customer_data.items() if v is not None}
                
                # Ensure required fields
                if not customer_data.get('created_at'):
                    customer_data['created_at'] = datetime.utcnow()
                
                customers.append(customer_data)
                
            except Exception as e:
                logger.error(f"Error transforming customer record: {e}")
                logger.debug(f"Record: {record}")
        
        return customers
    
    async def _transform_to_orders(
        self, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Transform data to Order model format."""
        
        orders = []
        
        for record in mysql_data:
            try:
                order_data = {
                    '_id': self._ensure_string_id(record.get('id') or record.get('order_id')),
                    'order_id': record.get('order_id') or f"ORD-{uuid.uuid4().hex[:8].upper()}",
                    'customer_id': self._ensure_string_id(record.get('customer_id') or record.get('user_id')),
                    'customer_name': record.get('customer_name') or record.get('user_name') or 'Unknown',
                    'customer_email': record.get('customer_email') or record.get('email', 'unknown@example.com'),
                    'order_date': self._convert_datetime(record.get('order_date') or record.get('created_at')),
                    'status': record.get('status') or record.get('order_status', 'pending'),
                    'total_amount': self._convert_to_float(record.get('total_amount') or record.get('total', 0)),
                    'shipping_address': record.get('shipping_address') or record.get('address'),
                    'payment_method': record.get('payment_method') or record.get('payment_type'),
                    'discount_applied': self._convert_to_float(record.get('discount_applied', 0.0)),
                    'shipping_cost': self._convert_to_float(record.get('shipping_cost', 0.0)),
                    'notes': record.get('notes') or record.get('comments'),
                    'fulfilled_date': self._convert_datetime(record.get('fulfilled_date')),
                    'items': []  # Will be populated separately if available
                }
                
                # Remove None values
                order_data = {k: v for k, v in order_data.items() if v is not None}
                
                # Ensure required fields
                if not order_data.get('order_date'):
                    order_data['order_date'] = datetime.utcnow()
                
                orders.append(order_data)
                
            except Exception as e:
                logger.error(f"Error transforming order record: {e}")
                logger.debug(f"Record: {record}")
        
        return orders
    
    async def _transform_to_inventory(
        self, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Transform data to Inventory model format."""
        
        inventory = []
        
        for record in mysql_data:
            try:
                inventory_data = {
                    '_id': self._ensure_string_id(record.get('id')),
                    'product_id': self._ensure_string_id(record.get('product_id')),
                    'product_name': record.get('product_name') or record.get('name', 'Unknown Product'),
                    'product_sku': record.get('product_sku') or record.get('sku', 'UNKNOWN'),
                    'quantity': int(record.get('quantity') or record.get('stock', 0)),
                    'reserved_quantity': int(record.get('reserved_quantity', 0)),
                    'available_quantity': int(record.get('available_quantity') or record.get('available', 0)),
                    'reorder_level': int(record.get('reorder_level', 10)),
                    'max_stock_level': int(record.get('max_stock_level', 1000)),
                    'low_stock_threshold': int(record.get('low_stock_threshold', 5)),
                    'last_updated': self._convert_datetime(record.get('last_updated') or record.get('updated_at')),
                    'supplier': record.get('supplier') or record.get('vendor'),
                    'cost_per_unit': self._convert_to_float(record.get('cost_per_unit') or record.get('unit_cost'))
                }
                
                # Calculate available quantity if not provided
                if 'available_quantity' not in record:
                    total_qty = inventory_data.get('quantity', 0)
                    reserved_qty = inventory_data.get('reserved_quantity', 0)
                    inventory_data['available_quantity'] = max(0, total_qty - reserved_qty)
                
                # Remove None values
                inventory_data = {k: v for k, v in inventory_data.items() if v is not None}
                
                # Ensure required fields
                if not inventory_data.get('last_updated'):
                    inventory_data['last_updated'] = datetime.utcnow()
                
                inventory.append(inventory_data)
                
            except Exception as e:
                logger.error(f"Error transforming inventory record: {e}")
                logger.debug(f"Record: {record}")
        
        return inventory
    
    async def _transform_generic(
        self, 
        mysql_data: List[Dict[str, Any]], 
        table_info: TableInfo
    ) -> List[Dict[str, Any]]:
        """Generic transformation for unknown table types."""
        
        transformed = []
        
        for record in mysql_data:
            try:
                transformed_record = {}
                
                for column_name, value in record.items():
                    # Map field names
                    mongodb_field = self.field_mappings.get(column_name.lower(), column_name)
                    
                    # Convert data types
                    column_type = table_info.columns.get(column_name, 'VARCHAR')
                    converted_value = self._convert_value(value, column_type)
                    
                    transformed_record[mongodb_field] = converted_value
                
                # Ensure _id field
                if '_id' not in transformed_record and 'id' in record:
                    transformed_record['_id'] = self._ensure_string_id(record['id'])
                elif '_id' not in transformed_record:
                    transformed_record['_id'] = str(uuid.uuid4())
                
                # Add timestamps if not present
                if 'created_at' not in transformed_record:
                    transformed_record['created_at'] = datetime.utcnow()
                if 'updated_at' not in transformed_record:
                    transformed_record['updated_at'] = datetime.utcnow()
                
                transformed.append(transformed_record)
                
            except Exception as e:
                logger.error(f"Error in generic transformation: {e}")
                logger.debug(f"Record: {record}")
        
        return transformed
    
    def _convert_value(self, value: Any, mysql_type: str) -> Any:
        """Convert a value based on MySQL column type."""
        if value is None:
            return None
        
        # Get base type (remove size specifications)
        base_type = mysql_type.split('(')[0].upper()
        
        converter = self.type_conversions.get(mysql_type) or self.type_conversions.get(base_type)
        if converter:
            return converter(value)
        
        return value
    
    def _convert_decimal(self, value) -> float:
        """Convert Decimal to float."""
        if isinstance(value, Decimal):
            return float(value)
        return self._convert_to_float(value)
    
    def _convert_datetime(self, value) -> Optional[datetime]:
        """Convert various datetime formats to datetime object."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Try common datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _convert_time(self, value) -> Optional[str]:
        """Convert time to string format."""
        if value is None:
            return None
        return str(value)
    
    def _convert_boolean(self, value) -> bool:
        """Convert various boolean representations."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('1', 'true', 'yes', 'on')
        return bool(value)
    
    def _convert_json(self, value) -> Any:
        """Convert JSON string to object."""
        if isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    
    def _convert_text(self, value) -> Optional[str]:
        """Convert text fields to string."""
        if value is None:
            return None
        return str(value)
    
    def _convert_to_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            if isinstance(value, Decimal):
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _ensure_string_id(self, value) -> str:
        """Ensure ID is a string."""
        if value is None:
            return str(uuid.uuid4())
        return str(value)