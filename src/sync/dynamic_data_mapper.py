"""
Dynamic Data Mapper - No Schema Required
Preserves ALL fields from MySQL to MongoDB without predefined schemas
Based on ChatGPT's recommendation for schema-less sync
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date, time, timezone
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class DynamicDataMapper:
    """
    Transforms MySQL data to MongoDB format WITHOUT predefined schemas.
    Automatically handles ALL fields dynamically.
    """

    def __init__(self):
        # Only handle data type conversions, not field mappings
        self.type_handlers = {
            datetime: lambda x: x.isoformat() if x else None,
            date: lambda x: x.isoformat() if x else None,
            time: lambda x: x.isoformat() if x else None,
            Decimal: lambda x: float(x) if x else 0.0,
            bytes: lambda x: x.decode('utf-8', errors='ignore') if x else '',
            memoryview: lambda x: x.tobytes().decode('utf-8', errors='ignore') if x else ''
        }

    async def transform_table_data(
        self,
        mysql_data: List[Dict[str, Any]],
        table_name: str,
        table_info: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Transform MySQL data to MongoDB format - preserves ALL fields.

        Args:
            mysql_data: Raw data from MySQL
            table_name: Name of the table (for logging)
            table_info: Optional table metadata (ignored for dynamic sync)

        Returns:
            List of documents ready for MongoDB insertion
        """

        logger.info(f"Transforming {len(mysql_data)} records from table: {table_name}")

        transformed_data = []

        for row in mysql_data:
            # Transform each row dynamically
            document = self._transform_row(row, table_name)

            # Add metadata fields if not present
            if '_sync_metadata' not in document:
                document['_sync_metadata'] = {
                    'source_table': table_name,
                    'synced_at': datetime.now(timezone.utc).isoformat(),
                    'sync_version': '2.0'  # Dynamic version
                }

            transformed_data.append(document)

        logger.info(f"Successfully transformed {len(transformed_data)} documents")
        return transformed_data

    def _transform_row(self, row: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """
        Transform a single row, preserving ALL fields.
        Only converts data types that MongoDB can't handle.
        """
        document = {}

        for field_name, value in row.items():
            # Keep original field name (no mapping)
            mongo_field = field_name

            # Convert value type if needed
            mongo_value = self._convert_value(value)

            document[mongo_field] = mongo_value

        return document

    def _convert_value(self, value: Any) -> Any:
        """
        Convert Python/MySQL types to MongoDB-compatible types.
        Returns original value if no conversion needed.
        """
        if value is None:
            return None

        # Check if value type needs conversion
        value_type = type(value)

        if value_type in self.type_handlers:
            return self.type_handlers[value_type](value)

        # Handle lists and dicts recursively
        if isinstance(value, list):
            return [self._convert_value(item) for item in value]

        if isinstance(value, dict):
            return {k: self._convert_value(v) for k, v in value.items()}

        # Return as-is for basic types (str, int, float, bool)
        return value

    async def get_table_primary_key(self, table_name: str, row: Dict[str, Any]) -> str:
        """
        Generate a unique key for upsert operations.
        Tries common primary key names, falls back to composite key.
        """
        # Common primary key field names
        pk_candidates = ['id', '_id', f'{table_name}_id', 'uuid', 'guid']

        for pk in pk_candidates:
            if pk in row and row[pk] is not None:
                return str(row[pk])

        # Fallback: create composite key from all non-null values
        # (not ideal for large tables, but ensures uniqueness)
        key_parts = []
        for k, v in sorted(row.items()):
            if v is not None and not k.startswith('_'):
                key_parts.append(f"{k}:{v}")

        if key_parts:
            # Create a hash of the composite key to keep it short
            import hashlib
            composite = "|".join(key_parts[:5])  # Use first 5 fields
            return hashlib.md5(composite.encode()).hexdigest()

        # Last resort: generate a new UUID
        import uuid
        return str(uuid.uuid4())

    def prepare_bulk_operations(
        self,
        documents: List[Dict[str, Any]],
        table_name: str,
        upsert: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Prepare bulk operations for MongoDB.
        Supports both insert and upsert operations.
        """
        operations = []

        for doc in documents:
            if upsert:
                # Try to find a unique identifier
                pk_fields = ['id', '_id', f'{table_name}_id']
                filter_doc = {}

                for pk in pk_fields:
                    if pk in doc and doc[pk] is not None:
                        filter_doc = {pk: doc[pk]}
                        break

                if not filter_doc:
                    # No primary key found, use the entire document as filter
                    # (this might create duplicates, but preserves all data)
                    filter_doc = {'_unique_hash': self._generate_doc_hash(doc)}
                    doc['_unique_hash'] = filter_doc['_unique_hash']

                operations.append({
                    'replaceOne': {
                        'filter': filter_doc,
                        'replacement': doc,
                        'upsert': True
                    }
                })
            else:
                # Simple insert
                operations.append({
                    'insertOne': {
                        'document': doc
                    }
                })

        return operations

    def _generate_doc_hash(self, doc: Dict[str, Any]) -> str:
        """Generate a hash for a document to use as unique identifier."""
        import hashlib

        # Create a deterministic string from document
        key_parts = []
        for k, v in sorted(doc.items()):
            if not k.startswith('_'):  # Skip metadata fields
                key_parts.append(f"{k}:{v}")

        doc_string = "|".join(key_parts[:10])  # Use first 10 fields
        return hashlib.sha256(doc_string.encode()).hexdigest()[:16]


# Global instance
dynamic_data_mapper = DynamicDataMapper()