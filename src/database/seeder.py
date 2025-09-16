"""
MongoDB database seeder - Disabled for production use.
Real data should be imported through proper channels.
"""

import logging
from src.database.mongodb import mongodb_client

logger = logging.getLogger(__name__)


class MongoDBSeeder:
    """Handles database seeding - currently disabled for production"""

    def __init__(self):
        self.categories = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports"]

    async def seed_all(self) -> bool:
        """Seed collections - disabled for production use"""
        logger.info("Database seeding is disabled - using real data only")
        return True

    async def clear_all_collections(self) -> bool:
        """Clear all collections - use with caution"""
        try:
            if not mongodb_client.is_connected:
                await mongodb_client.connect()

            db = mongodb_client.database

            # List of collections to clear
            collections = ["products", "customers", "orders", "inventory"]

            for collection_name in collections:
                result = await db[collection_name].delete_many({})
                logger.info(f"Cleared {result.deleted_count} documents from {collection_name}")

            logger.info("✅ All collections cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collections: {e}", exc_info=True)
            return False


# Global seeder instance
mongodb_seeder = MongoDBSeeder()