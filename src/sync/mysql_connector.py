"""
MySQL Connector with automatic table discovery and schema inspection.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiomysql
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """Information about a MySQL table."""
    name: str
    columns: Dict[str, str]  # column_name -> data_type
    primary_key: Optional[str] = None
    has_created_at: bool = False
    has_updated_at: bool = False
    created_at_column: Optional[str] = None
    updated_at_column: Optional[str] = None


@dataclass
class MySQLConnectionConfig:
    """MySQL connection configuration."""
    host: str
    user: str
    password: str
    database: str
    port: int = 3306
    charset: str = "utf8mb4"
    min_pool_size: int = 1
    max_pool_size: int = 10
    pool_timeout: int = 30


class MySQLConnector:
    """
    MySQL connector with automatic table discovery and schema inspection.
    Discovers all tables in the database and analyzes their structure.
    """
    
    def __init__(self, config: MySQLConnectionConfig):
        self.config = config
        self.pool: Optional[aiomysql.Pool] = None
        self.discovered_tables: Dict[str, TableInfo] = {}
        self.is_connected = False
    
    async def connect(self) -> bool:
        """Establish connection to MySQL database."""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                db=self.config.database,
                charset=self.config.charset,
                minsize=self.config.min_pool_size,
                maxsize=self.config.max_pool_size,
                connect_timeout=self.config.pool_timeout,
                autocommit=True,
                # Add these for better connection management
                pool_recycle=3600,  # Recycle connections every hour
                echo=False
            )
            self.is_connected = True
            logger.info(f"Connected to MySQL database: {self.config.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Close database connection."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.is_connected = False
            logger.info("Disconnected from MySQL database")
    
    async def discover_all_tables(self) -> Dict[str, TableInfo]:
        """
        Discover all tables in the database and analyze their structure.
        Returns a dictionary of table_name -> TableInfo.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MySQL database")
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Get all table names
                    await cursor.execute("SHOW TABLES")
                    tables = await cursor.fetchall()
                    
                    self.discovered_tables = {}
                    
                    for (table_name,) in tables:
                        try:
                            table_info = await self._analyze_table_structure(cursor, table_name)
                            self.discovered_tables[table_name] = table_info
                            logger.info(f"Discovered table: {table_name}")
                        except Exception as e:
                            logger.warning(f"Failed to analyze table {table_name}: {e}")
                    
                    logger.info(f"Discovered {len(self.discovered_tables)} tables total")
                    return self.discovered_tables
        
        except Exception as e:
            logger.error(f"Error during table discovery: {e}")
            # Mark connection as lost and raise
            self.is_connected = False
            raise
    
    async def _analyze_table_structure(self, cursor, table_name: str) -> TableInfo:
        """Analyze the structure of a specific table."""
        # Get column information
        await cursor.execute(f"DESCRIBE `{table_name}`")
        columns_info = await cursor.fetchall()
        
        columns = {}
        primary_key = None
        created_at_column = None
        updated_at_column = None
        
        for column_info in columns_info:
            column_name = column_info[0]
            data_type = column_info[1]
            key_type = column_info[3]  # PRI, UNI, MUL, or empty
            
            columns[column_name] = data_type
            
            # Identify primary key
            if key_type == 'PRI':
                primary_key = column_name
            
            # Look for timestamp columns (common patterns)
            column_lower = column_name.lower()
            if column_lower in ['created_at', 'date_created', 'create_time', 'created']:
                created_at_column = column_name
            elif column_lower in ['updated_at', 'date_updated', 'update_time', 'modified', 'last_modified']:
                updated_at_column = column_name
        
        return TableInfo(
            name=table_name,
            columns=columns,
            primary_key=primary_key,
            has_created_at=created_at_column is not None,
            has_updated_at=updated_at_column is not None,
            created_at_column=created_at_column,
            updated_at_column=updated_at_column
        )
    
    async def get_tables_with_timestamps(self) -> Dict[str, TableInfo]:
        """Get only tables that have timestamp columns for incremental sync."""
        if not self.discovered_tables:
            await self.discover_all_tables()
        
        timestamp_tables = {
            name: info for name, info in self.discovered_tables.items()
            if info.has_created_at or info.has_updated_at
        }
        
        logger.info(f"Found {len(timestamp_tables)} tables with timestamp columns")
        return timestamp_tables
    
    async def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample data from a table to understand its structure."""
        if not self.is_connected:
            raise RuntimeError("Not connected to MySQL database")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(f"SELECT * FROM `{table_name}` LIMIT %s", (limit,))
                return await cursor.fetchall()
    
    async def get_table_count(self, table_name: str) -> int:
        """Get total record count for a table."""
        if not self.is_connected:
            raise RuntimeError("Not connected to MySQL database")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def get_incremental_data(
        self, 
        table_name: str, 
        last_sync: Optional[datetime] = None,
        batch_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get incremental data from a table since last sync.
        Uses timestamp columns to fetch only new/updated records.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MySQL database")
        
        table_info = self.discovered_tables.get(table_name)
        if not table_info:
            raise ValueError(f"Table {table_name} not found in discovered tables")
        
        # Build query with timestamp filter
        where_clause = ""
        params = []
        
        if last_sync and (table_info.has_created_at or table_info.has_updated_at):
            conditions = []
            
            if table_info.created_at_column:
                conditions.append(f"`{table_info.created_at_column}` > %s")
                params.append(last_sync)
            
            if table_info.updated_at_column and table_info.updated_at_column != table_info.created_at_column:
                conditions.append(f"`{table_info.updated_at_column}` > %s")
                params.append(last_sync)
            
            if conditions:
                where_clause = f"WHERE ({' OR '.join(conditions)})"
        
        query = f"SELECT * FROM `{table_name}` {where_clause} LIMIT %s"
        params.append(batch_size)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
    
    def print_discovered_tables(self):
        """Print a summary of all discovered tables."""
        if not self.discovered_tables:
            print("No tables discovered yet. Run discover_all_tables() first.")
            return
        
        print(f"\n=== Discovered {len(self.discovered_tables)} Tables ===")
        print(f"Database: {self.config.database}")
        print("-" * 80)
        
        for table_name, info in self.discovered_tables.items():
            print(f"\nTable: {table_name}")
            print(f"  Primary Key: {info.primary_key or 'None'}")
            print(f"  Created At: {info.created_at_column or 'None'}")
            print(f"  Updated At: {info.updated_at_column or 'None'}")
            print(f"  Columns ({len(info.columns)}):")
            for col_name, col_type in info.columns.items():
                marker = ""
                if col_name == info.primary_key:
                    marker = " (PK)"
                elif col_name == info.created_at_column:
                    marker = " (CREATED)"
                elif col_name == info.updated_at_column:
                    marker = " (UPDATED)"
                print(f"    - {col_name}: {col_type}{marker}")
    
    async def get_foreign_key_relationships(self, table_name: str) -> List[Dict[str, str]]:
        """Get foreign key relationships for a table."""
        if not self.is_connected:
            raise RuntimeError("Not connected to MySQL database")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                SELECT 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """
                await cursor.execute(query, (self.config.database, table_name))
                return [
                    {
                        "column": row[0],
                        "referenced_table": row[1],
                        "referenced_column": row[2]
                    }
                    for row in await cursor.fetchall()
                ]