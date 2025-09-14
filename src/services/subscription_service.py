"""
Subscription management service for handling user subscriptions and token limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from bson import ObjectId

from src.database.mongodb import mongodb_client
from src.models.api import (
    SubscriptionRequest, SubscriptionResponse, SubscriptionStatusResponse,
    QueryContext
)
from src.models.mongodb_models import UserSubscription, UserTokenUsage

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing user subscriptions and token usage"""

    async def create_or_update_subscription(
        self,
        request: SubscriptionRequest,
        context: QueryContext
    ) -> SubscriptionResponse:
        """Create or update user subscription"""

        user_id = context.user_id
        shop_id = context.shop_id

        try:
            # Check for existing subscription
            existing_sub = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": {"$in": ["active", "suspended"]}
            })

            if existing_sub and request.action == "create":
                # Update existing subscription instead of creating new
                return await self._update_existing_subscription(existing_sub, request, context)
            elif existing_sub:
                # Handle upgrade/downgrade
                return await self._update_existing_subscription(existing_sub, request, context)
            else:
                # Create new subscription
                return await self._create_new_subscription(request, context)

        except Exception as e:
            logger.error(f"Failed to create/update subscription for user {user_id}: {e}", exc_info=True)
            raise e

    async def _create_new_subscription(
        self,
        request: SubscriptionRequest,
        context: QueryContext
    ) -> SubscriptionResponse:
        """Create new subscription"""

        user_id = context.user_id
        shop_id = context.shop_id

        # Calculate billing dates
        start_date = datetime.utcnow()
        if request.billing_cycle == "monthly":
            period_end = start_date + timedelta(days=30)
            next_billing = period_end
        else:  # yearly
            period_end = start_date + timedelta(days=365)
            next_billing = period_end

        # Create subscription record
        subscription = UserSubscription(
            user_id=user_id,
            shop_id=shop_id,
            plan_name=request.plan_name,
            plan_display_name=request.plan_display_name,
            allocated_tokens=request.allocated_tokens,
            monthly_fee=request.monthly_fee,
            currency=request.currency,
            billing_cycle=request.billing_cycle,
            subscription_start_date=start_date,
            current_period_start=start_date,
            current_period_end=period_end,
            next_billing_date=next_billing,
            status="active"
        )

        # Insert subscription
        result = await mongodb_client.database.subscriptions.insert_one(subscription.dict(by_alias=True))
        subscription_id = str(result.inserted_id)

        # Create corresponding token usage record
        await self._create_token_usage_record(subscription_id, user_id, shop_id, start_date, period_end)

        logger.info(f"Created new subscription {subscription_id} for user {user_id}")

        return SubscriptionResponse(
            subscription_id=subscription_id,
            user_id=user_id,
            shop_id=shop_id,
            plan_name=request.plan_name,
            plan_display_name=request.plan_display_name,
            allocated_tokens=request.allocated_tokens,
            monthly_fee=request.monthly_fee,
            currency=request.currency,
            status="active",
            current_period_start=start_date,
            current_period_end=period_end,
            next_billing_date=next_billing,
            current_usage=0,
            remaining_tokens=request.allocated_tokens,
            usage_percentage=0.0,
            action_performed="create",
            effective_date=start_date,
            message=f"Successfully created {request.plan_display_name} subscription"
        )

    async def _update_existing_subscription(
        self,
        existing_sub: Dict,
        request: SubscriptionRequest,
        context: QueryContext
    ) -> SubscriptionResponse:
        """Update existing subscription"""

        user_id = context.user_id
        subscription_id = existing_sub["_id"]  # Keep as is, don't convert to string yet
        subscription_id_str = str(subscription_id)  # String version for references
        previous_plan = existing_sub["plan_name"]
        previous_tokens = existing_sub["allocated_tokens"]

        # Get current token usage
        token_usage = await mongodb_client.database.token_usage.find_one({
            "user_id": user_id,
            "subscription_id": subscription_id_str
        })
        current_usage = token_usage["used_tokens"] if token_usage else 0

        # Handle plan changes
        if request.allocated_tokens < previous_tokens and current_usage > request.allocated_tokens:
            # Downgrade with overage - block until next period
            logger.warning(f"User {user_id} downgrading with usage overage: {current_usage} > {request.allocated_tokens}")
            remaining_tokens = 0
            status = "active"  # Keep active but with 0 remaining
        else:
            remaining_tokens = max(0, request.allocated_tokens - current_usage)
            status = "active"

        # Add to plan history
        plan_history_entry = {
            "plan": previous_plan,
            "tokens": previous_tokens,
            "fee": existing_sub["monthly_fee"],
            "start_date": existing_sub["current_period_start"],
            "end_date": datetime.utcnow(),
            "change_reason": request.action
        }

        # Update subscription
        update_data = {
            "plan_name": request.plan_name,
            "plan_display_name": request.plan_display_name,
            "allocated_tokens": request.allocated_tokens,
            "monthly_fee": request.monthly_fee,
            "currency": request.currency,
            "status": status,
            "updated_at": datetime.utcnow()
        }

        await mongodb_client.database.subscriptions.update_one(
            {"_id": subscription_id},  # Use original _id without ObjectId conversion
            {
                "$set": update_data,
                "$push": {"plan_history": plan_history_entry}
            }
        )

        logger.info(f"Updated subscription {subscription_id} for user {user_id}: {previous_plan} -> {request.plan_name}")

        return SubscriptionResponse(
            subscription_id=subscription_id_str,
            user_id=user_id,
            shop_id=context.shop_id,
            plan_name=request.plan_name,
            plan_display_name=request.plan_display_name,
            allocated_tokens=request.allocated_tokens,
            monthly_fee=request.monthly_fee,
            currency=request.currency,
            status=status,
            current_period_start=existing_sub["current_period_start"],
            current_period_end=existing_sub["current_period_end"],
            next_billing_date=existing_sub["next_billing_date"],
            current_usage=current_usage,
            remaining_tokens=remaining_tokens,
            usage_percentage=round((current_usage / request.allocated_tokens) * 100, 2) if request.allocated_tokens > 0 else 0,
            action_performed=request.action,
            previous_plan=previous_plan,
            effective_date=datetime.utcnow(),
            message=f"Successfully {request.action}d to {request.plan_display_name}"
        )

    async def _create_token_usage_record(
        self,
        subscription_id: str,
        user_id: str,
        shop_id: str,
        period_start: datetime,
        period_end: datetime
    ):
        """Create initial token usage record for new subscription"""

        token_usage = UserTokenUsage(
            user_id=user_id,
            shop_id=shop_id,
            subscription_id=subscription_id,
            used_tokens=0,
            current_period_start=period_start,
            current_period_end=period_end,
            daily_usage=[],
            total_queries=0,
            avg_tokens_per_query=0.0
        )

        await mongodb_client.database.token_usage.insert_one(token_usage.dict(by_alias=True))
        logger.info(f"Created token usage record for user {user_id}")

    async def get_subscription_status(
        self,
        context: QueryContext,
        include_history: bool = False
    ) -> Optional[SubscriptionStatusResponse]:
        """Get comprehensive subscription status"""

        user_id = context.user_id
        shop_id = context.shop_id

        try:
            # Get active subscription
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "shop_id": shop_id,
                "status": {"$in": ["active", "suspended"]}
            })

            if not subscription:
                return None

            subscription_id = str(subscription["_id"])

            # Get token usage
            token_usage = await mongodb_client.database.token_usage.find_one({
                "user_id": user_id,
                "subscription_id": subscription_id
            })

            current_usage = token_usage["used_tokens"] if token_usage else 0
            allocated_tokens = subscription["allocated_tokens"]
            remaining_tokens = max(0, allocated_tokens - current_usage)
            usage_percentage = round((current_usage / allocated_tokens) * 100, 2) if allocated_tokens > 0 else 0

            # Calculate analytics
            analytics = await self._calculate_usage_analytics(token_usage) if token_usage else {
                "avg_daily_usage": 0.0,
                "projected_monthly_usage": 0.0,
                "usage_trend": "stable"
            }

            # Calculate days remaining
            days_remaining = max(0, (subscription["current_period_end"] - datetime.utcnow()).days)

            # Generate alerts and recommendations
            alerts = self._generate_alerts(subscription, current_usage, allocated_tokens, usage_percentage)
            recommendations = self._generate_recommendations(subscription, analytics, usage_percentage)

            return SubscriptionStatusResponse(
                user_id=user_id,
                shop_id=shop_id,
                subscription_id=subscription_id,
                plan_name=subscription["plan_name"],
                plan_display_name=subscription["plan_display_name"],
                status=subscription["status"],
                allocated_tokens=allocated_tokens,
                monthly_fee=subscription["monthly_fee"],
                currency=subscription["currency"],
                current_usage=current_usage,
                remaining_tokens=remaining_tokens,
                usage_percentage=usage_percentage,
                current_period_start=subscription["current_period_start"],
                current_period_end=subscription["current_period_end"],
                days_remaining_in_period=days_remaining,
                next_billing_date=subscription["next_billing_date"],
                next_billing_amount=subscription["monthly_fee"],
                avg_daily_usage=analytics["avg_daily_usage"],
                projected_monthly_usage=analytics["projected_monthly_usage"],
                usage_trend=analytics["usage_trend"],
                alerts=alerts,
                recommendations=recommendations,
                usage_history=analytics.get("usage_history", {}) if include_history else {},
                plan_history=subscription.get("plan_history", []) if include_history else []
            )

        except Exception as e:
            logger.error(f"Failed to get subscription status for user {user_id}: {e}", exc_info=True)
            raise e

    async def _calculate_usage_analytics(self, token_usage: Dict) -> Dict[str, Any]:
        """Calculate usage analytics"""

        if not token_usage or not token_usage.get("daily_usage"):
            return {
                "avg_daily_usage": 0.0,
                "projected_monthly_usage": 0.0,
                "usage_trend": "stable",
                "usage_history": {}
            }

        daily_usage = token_usage["daily_usage"]

        # Calculate average daily usage (last 7 days)
        recent_usage = daily_usage[-7:] if len(daily_usage) >= 7 else daily_usage
        avg_daily_usage = sum(day.get("tokens", 0) for day in recent_usage) / len(recent_usage) if recent_usage else 0

        # Project monthly usage
        days_in_period = (token_usage["current_period_end"] - token_usage["current_period_start"]).days
        projected_monthly_usage = avg_daily_usage * days_in_period

        # Determine usage trend
        if len(daily_usage) >= 3:
            recent_avg = sum(day.get("tokens", 0) for day in daily_usage[-3:]) / 3
            older_avg = sum(day.get("tokens", 0) for day in daily_usage[-6:-3]) / 3 if len(daily_usage) >= 6 else recent_avg

            if recent_avg > older_avg * 1.1:
                usage_trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                usage_trend = "decreasing"
            else:
                usage_trend = "stable"
        else:
            usage_trend = "stable"

        return {
            "avg_daily_usage": round(avg_daily_usage, 2),
            "projected_monthly_usage": round(projected_monthly_usage, 0),
            "usage_trend": usage_trend,
            "usage_history": {
                "daily": daily_usage[-30:],  # Last 30 days
                "total_queries": token_usage.get("total_queries", 0),
                "avg_tokens_per_query": token_usage.get("avg_tokens_per_query", 0)
            }
        }

    def _generate_alerts(self, subscription: Dict, current_usage: int, allocated_tokens: int, usage_percentage: float) -> List[Dict]:
        """Generate usage alerts"""

        alerts = []

        if usage_percentage >= 90:
            alerts.append({
                "type": "error",
                "message": f"Critical: {usage_percentage:.1f}% of monthly tokens used",
                "action": "Consider upgrading immediately"
            })
        elif usage_percentage >= 75:
            alerts.append({
                "type": "warning",
                "message": f"High usage: {usage_percentage:.1f}% of monthly tokens used",
                "action": "Monitor usage closely"
            })
        elif usage_percentage >= 50:
            alerts.append({
                "type": "info",
                "message": f"Moderate usage: {usage_percentage:.1f}% of monthly tokens used",
                "action": "Usage is on track"
            })

        # Check if subscription expires soon
        days_remaining = (subscription["current_period_end"] - datetime.utcnow()).days
        if days_remaining <= 3:
            alerts.append({
                "type": "info",
                "message": f"Subscription renews in {days_remaining} days",
                "action": "Ensure payment method is up to date"
            })

        return alerts

    def _generate_recommendations(self, subscription: Dict, analytics: Dict, usage_percentage: float) -> List[str]:
        """Generate usage recommendations"""

        recommendations = []
        plan_name = subscription["plan_name"]
        projected_usage = analytics.get("projected_monthly_usage", 0)
        allocated_tokens = subscription["allocated_tokens"]

        # Upgrade recommendations
        if usage_percentage > 80 or projected_usage > allocated_tokens * 0.9:
            if plan_name == "basic":
                recommendations.append("Consider upgrading to Pro plan for 4x more tokens")
            elif plan_name == "pro":
                recommendations.append("Consider upgrading to Enterprise plan for 5x more tokens")

        # Usage optimization
        if analytics.get("usage_trend") == "increasing":
            recommendations.append("Usage is increasing - monitor your query patterns")

        # Efficiency recommendations
        avg_tokens = analytics.get("usage_history", {}).get("avg_tokens_per_query", 0)
        if avg_tokens > 300:
            recommendations.append("Consider optimizing queries - current average is high")

        return recommendations

    async def get_user_subscription(self, user_id: str, shop_id: str) -> Optional[Dict]:
        """Get user's active subscription (for internal use)"""

        return await mongodb_client.database.subscriptions.find_one({
            "user_id": user_id,
            "shop_id": shop_id,
            "status": "active"
        })

    async def check_monthly_reset_needed(self, user_id: str) -> bool:
        """Check if user needs monthly reset"""

        token_usage = await mongodb_client.database.token_usage.find_one({"user_id": user_id})

        if not token_usage:
            return False

        current_period_end = token_usage.get("current_period_end")
        if not current_period_end:
            return False

        return datetime.utcnow() > current_period_end

    async def perform_monthly_reset(self, user_id: str) -> bool:
        """Perform monthly reset for user"""

        try:
            # Get subscription for new period dates
            subscription = await mongodb_client.database.subscriptions.find_one({
                "user_id": user_id,
                "status": "active"
            })

            if not subscription:
                return False

            # Calculate new period
            now = datetime.utcnow()
            if subscription["billing_cycle"] == "monthly":
                new_period_end = now + timedelta(days=30)
            else:
                new_period_end = now + timedelta(days=365)

            # Reset token usage
            result = await mongodb_client.database.token_usage.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "used_tokens": 0,
                        "current_period_start": now,
                        "current_period_end": new_period_end,
                        "last_updated": now,
                        "total_queries": 0,
                        "avg_tokens_per_query": 0.0,
                        "peak_daily_usage": 0
                    },
                    "$push": {
                        "monthly_summary": {
                            "month": now.strftime("%Y-%m"),
                            "reset_date": now,
                            "reason": "monthly_reset"
                        }
                    },
                    "$unset": {
                        "daily_usage": "",
                        "weekly_usage": ""
                    }
                }
            )

            # Update subscription period
            await mongodb_client.database.subscriptions.update_one(
                {"user_id": user_id, "status": "active"},
                {
                    "$set": {
                        "current_period_start": now,
                        "current_period_end": new_period_end,
                        "next_billing_date": new_period_end,
                        "updated_at": now
                    }
                }
            )

            logger.info(f"Performed monthly reset for user {user_id}")
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to perform monthly reset for user {user_id}: {e}", exc_info=True)
            return False


# Global subscription service instance
subscription_service = SubscriptionService()