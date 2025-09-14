"""
Token usage tracking and management service.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from bson import ObjectId

from src.database.mongodb import mongodb_client
from src.models.api import UserTokenInfo, SubscriptionInfo

logger = logging.getLogger(__name__)


class TokenService:
    """Service for tracking and managing token usage"""

    async def check_token_availability(
        self,
        user_id: str,
        shop_id: str,
        estimated_tokens: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user has sufficient tokens for query
        Returns: (can_proceed, info_dict)
        """

        try:
            # Get active subscription
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": "active"
            })

            if not subscription:
                return False, {
                    "error": "NO_SUBSCRIPTION",
                    "message": "No active subscription found. Please subscribe first.",
                    "can_proceed": False
                }

            # Get current usage
            token_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": str(subscription["_id"])
            })

            if not token_usage:
                # Create token usage record if missing
                await self._create_missing_token_usage(user_id, shop_id, str(subscription["_id"]))
                current_usage = 0
            else:
                # Check if monthly reset needed
                if await self._check_and_perform_reset(user_id, token_usage):
                    current_usage = 0  # After reset
                else:
                    current_usage = token_usage["used_tokens"]

            allocated_tokens = subscription["allocated_tokens"]
            remaining_tokens = max(0, allocated_tokens - current_usage)

            # Check availability
            if current_usage + estimated_tokens > allocated_tokens:
                return False, {
                    "error": "TOKEN_LIMIT_EXCEEDED",
                    "message": f"Monthly token limit ({allocated_tokens:,}) would be exceeded",
                    "current_usage": current_usage,
                    "allocated_tokens": allocated_tokens,
                    "remaining_tokens": remaining_tokens,
                    "estimated_tokens": estimated_tokens,
                    "can_proceed": False
                }

            return True, {
                "current_usage": current_usage,
                "allocated_tokens": allocated_tokens,
                "remaining_tokens": remaining_tokens - estimated_tokens,  # After this query
                "estimated_tokens": estimated_tokens,
                "can_proceed": True,
                "subscription": {
                    "plan": subscription["plan_name"],
                    "status": subscription["status"]
                }
            }

        except Exception as e:
            logger.error(f"Error checking token availability for user {user_id}: {e}", exc_info=True)
            return False, {
                "error": "TOKEN_CHECK_FAILED",
                "message": "Unable to check token availability",
                "can_proceed": False
            }

    async def update_token_usage(
        self,
        user_id: str,
        shop_id: str,
        actual_tokens_used: int,
        query_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Update token usage after query completion"""

        try:
            # Get subscription
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": "active"
            })

            if not subscription:
                logger.warning(f"No subscription found for user {user_id} during usage update")
                return {"success": False, "error": "No subscription found"}

            subscription_id = str(subscription["_id"])
            today = datetime.utcnow().date().isoformat()

            # Prepare daily usage entry
            daily_entry = {
                "date": today,
                "tokens": actual_tokens_used,
                "timestamp": datetime.utcnow(),
                "query_id": query_info.get("query_id") if query_info else None
            }

            # Update token usage with atomic operations
            result = await mongodb_client.database.token_usage.update_one(
                {
                    "user_id": user_id,
                    "subscription_id": subscription_id
                },
                {
                    "$inc": {
                        "used_tokens": actual_tokens_used,
                        "total_queries": 1
                    },
                    "$set": {
                        "last_updated": datetime.utcnow()
                    },
                    "$push": {
                        "daily_usage": {
                            "$each": [daily_entry],
                            "$slice": -30  # Keep only last 30 days
                        }
                    }
                },
                upsert=True
            )

            if result.modified_count == 0 and result.upserted_id is None:
                logger.warning(f"Token usage update had no effect for user {user_id}")

            # Update average tokens per query
            await self._update_query_average(user_id, subscription_id)

            # Get updated usage for response
            updated_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": subscription_id
            })

            current_usage = updated_usage["used_tokens"] if updated_usage else actual_tokens_used
            allocated_tokens = subscription["allocated_tokens"]
            remaining_tokens = max(0, allocated_tokens - current_usage)
            usage_percentage = round((current_usage / allocated_tokens) * 100, 2) if allocated_tokens > 0 else 0

            logger.info(f"Updated token usage for user {user_id}: +{actual_tokens_used} tokens (total: {current_usage})")

            return {
                "success": True,
                "used_tokens": actual_tokens_used,
                "total_used": current_usage,
                "allocated_tokens": allocated_tokens,
                "remaining_tokens": remaining_tokens,
                "usage_percentage": usage_percentage
            }

        except Exception as e:
            logger.error(f"Failed to update token usage for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _update_query_average(self, user_id: str, subscription_id: str):
        """Update average tokens per query"""

        try:
            token_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": subscription_id
            })

            if token_usage and token_usage.get("total_queries", 0) > 0:
                avg_tokens = token_usage["used_tokens"] / token_usage["total_queries"]

                await mongodb_client.database.token_usage.update_one(
                    {"user_id": user_id, "subscription_id": subscription_id},
                    {"$set": {"avg_tokens_per_query": round(avg_tokens, 2)}}
                )

        except Exception as e:
            logger.error(f"Failed to update query average for user {user_id}: {e}")

    async def _check_and_perform_reset(self, user_id: str, token_usage: Dict) -> bool:
        """Check if monthly reset is needed and perform it"""

        current_period_end = token_usage.get("current_period_end")
        if not current_period_end:
            return False

        if datetime.utcnow() > current_period_end:
            # Import here to avoid circular import
            from src.services.subscription_service import subscription_service
            return await subscription_service.perform_monthly_reset(user_id)

        return False

    async def _create_missing_token_usage(self, user_id: str, shop_id: str, subscription_id: str):
        """Create missing token usage record"""

        try:
            now = datetime.utcnow()
            period_end = now + timedelta(days=30)

            token_usage_data = {
                "_id": ObjectId(),
                "user_id": user_id,
                "shop_id": shop_id,
                "subscription_id": subscription_id,
                "used_tokens": 0,
                "current_period_start": now,
                "current_period_end": period_end,
                "daily_usage": [],
                "weekly_usage": [],
                "monthly_summary": [],
                "total_queries": 0,
                "avg_tokens_per_query": 0.0,
                "peak_daily_usage": 0,
                "created_at": now,
                "last_updated": now
            }

            await mongodb_client.database.token_usage.insert_one(token_usage_data)
            logger.info(f"Created missing token usage record for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to create missing token usage record for user {user_id}: {e}")

    def estimate_query_tokens(self, query: str, options: Optional[Dict] = None) -> int:
        """Estimate tokens needed for a query"""

        # Basic estimation logic
        base_tokens = 100  # System prompt and overhead

        # Estimate based on query length
        query_words = len(query.split())
        query_tokens = int(query_words * 1.3)  # ~1.3 tokens per word

        # Estimate response tokens based on query complexity
        if any(keyword in query.lower() for keyword in ["detailed", "analyze", "comprehensive", "report"]):
            response_tokens = 300  # Detailed response
        elif any(keyword in query.lower() for keyword in ["list", "show", "get", "find"]):
            response_tokens = 150  # Moderate response
        else:
            response_tokens = 100  # Simple response

        # Preferred model adjustment
        if options and options.get("preferred_model"):
            model = options["preferred_model"].lower()
            if "70b" in model or "large" in model:
                base_tokens = int(base_tokens * 1.5)  # Larger models use more tokens

        total_estimated = base_tokens + query_tokens + response_tokens

        # Add 20% buffer for safety
        return int(total_estimated * 1.2)

    async def get_user_token_info(
        self,
        user_id: str,
        shop_id: str,
        tokens_used_this_query: int = 0
    ) -> Optional[UserTokenInfo]:
        """Get user token information for response"""

        try:
            # Get subscription
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": "active"
            })

            if not subscription:
                return None

            # Get token usage
            token_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": str(subscription["_id"])
            })

            current_usage = token_usage["used_tokens"] if token_usage else 0
            allocated_tokens = subscription["allocated_tokens"]
            remaining_tokens = max(0, allocated_tokens - current_usage)
            usage_percentage = round((current_usage / allocated_tokens) * 100, 2) if allocated_tokens > 0 else 0

            # Estimate remaining queries
            avg_tokens_per_query = token_usage.get("avg_tokens_per_query", 200) if token_usage else 200
            if avg_tokens_per_query > 0:
                queries_remaining_estimate = max(0, int(remaining_tokens / avg_tokens_per_query))
            else:
                queries_remaining_estimate = None

            return UserTokenInfo(
                used_this_query=tokens_used_this_query,
                total_used_this_month=current_usage,
                allocated_tokens=allocated_tokens,
                remaining_tokens=remaining_tokens,
                usage_percentage=usage_percentage,
                queries_remaining_estimate=queries_remaining_estimate
            )

        except Exception as e:
            logger.error(f"Failed to get user token info for {user_id}: {e}")
            return None

    async def get_subscription_info(
        self,
        user_id: str,
        shop_id: str
    ) -> Optional[SubscriptionInfo]:
        """Get subscription information for response"""

        try:
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": "active"
            })

            if not subscription:
                return None

            days_remaining = max(0, (subscription["current_period_end"] - datetime.utcnow()).days)

            return SubscriptionInfo(
                plan=subscription["plan_name"],
                status=subscription["status"],
                days_remaining=days_remaining
            )

        except Exception as e:
            logger.error(f"Failed to get subscription info for {user_id}: {e}")
            return None

    async def get_usage_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive usage summary for analytics"""

        try:
            # Get subscription
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "status": "active"
            })

            if not subscription:
                return {"error": "No active subscription"}

            # Get token usage
            token_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": str(subscription["_id"])
            })

            if not token_usage:
                return {"error": "No usage data found"}

            current_usage = token_usage["used_tokens"]
            allocated_tokens = subscription["allocated_tokens"]

            return {
                "user_id": user_id,
                "plan": subscription["plan_name"],
                "allocated_tokens": allocated_tokens,
                "current_usage": current_usage,
                "remaining_tokens": max(0, allocated_tokens - current_usage),
                "usage_percentage": round((current_usage / allocated_tokens) * 100, 2) if allocated_tokens > 0 else 0,
                "total_queries": token_usage.get("total_queries", 0),
                "avg_tokens_per_query": token_usage.get("avg_tokens_per_query", 0),
                "period_start": token_usage["current_period_start"],
                "period_end": token_usage["current_period_end"],
                "last_updated": token_usage["last_updated"]
            }

        except Exception as e:
            logger.error(f"Failed to get usage summary for user {user_id}: {e}")
            return {"error": str(e)}


# Global token service instance
token_service = TokenService()