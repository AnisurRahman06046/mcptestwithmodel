"""
Subscription management API routes.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header

from src.models.api import (
    SubscriptionRequest, SubscriptionResponse, SubscriptionStatusResponse,
    QueryContext
)
from src.services.auth_service import auth_service
from src.services.subscription_service import subscription_service
from src.sync.sync_service import SyncService

logger = logging.getLogger(__name__)
sync_service = SyncService()  # Create instance

router = APIRouter(prefix="/api/v1", tags=["subscription"])


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_or_update_subscription(
    request: SubscriptionRequest,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Create or update user subscription

    This endpoint is called by the platform when a user:
    - Creates a new subscription
    - Upgrades their plan
    - Downgrades their plan
    - Updates subscription details
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Ensure user exists locally (with fallback sync if needed)
        await _ensure_user_exists_locally(context.user_id, context.shop_id)

        # Create or update subscription
        result = await subscription_service.create_or_update_subscription(request, context)

        logger.info(f"Subscription {request.action} successful for user {context.user_id}: {request.plan_name}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription operation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process subscription request"
        )


@router.get("/subscription/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    include_history: bool = False,
    days: int = 30,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Get comprehensive subscription status and usage analytics

    This endpoint is called by the platform to:
    - Display user's current subscription details
    - Show token usage statistics
    - Provide usage analytics and recommendations
    - Display billing information
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Get subscription status
        status = await subscription_service.get_subscription_status(
            context, include_history
        )

        if not status:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found for this user"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve subscription status"
        )


@router.get("/subscription/{user_id}/status", response_model=SubscriptionStatusResponse)
async def get_user_subscription_status(
    user_id: str,
    shop_id: Optional[str] = None,
    include_history: bool = False,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Get subscription status for a specific user (admin endpoint)

    This endpoint can be used by platform administrators to:
    - Check any user's subscription status
    - Debug subscription issues
    - Generate reports
    """

    try:
        # Authenticate request (should verify admin permissions)
        context = await auth_service.authenticate_request(authorization)

        # Create context for target user
        target_context = QueryContext(
            user_id=user_id,
            shop_id=shop_id or context.shop_id,
            timezone=context.timezone,
            currency=context.currency
        )

        # Get subscription status
        status = await subscription_service.get_subscription_status(
            target_context, include_history
        )

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"No active subscription found for user {user_id}"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription status for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user subscription status"
        )


@router.delete("/subscription")
async def cancel_subscription(
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Cancel user subscription

    This endpoint is called when a user cancels their subscription.
    The subscription will remain active until the end of the current billing period.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Cancel subscription (set status to cancelled)
        from src.database.mongodb import mongodb_client

        result = await mongodb_client.database.subscriptions.update_one(
            {
                "user_id": context.user_id,
                "shop_id": context.shop_id,
                "status": "active"
            },
            {
                "$set": {
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found to cancel"
            )

        logger.info(f"Cancelled subscription for user {context.user_id}")

        return {
            "success": True,
            "message": "Subscription cancelled successfully. Access will continue until the end of current billing period.",
            "cancelled_at": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel subscription"
        )


@router.post("/subscription/{user_id}/reset-usage")
async def reset_user_usage(
    user_id: str,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Reset user's monthly token usage (admin endpoint)

    This endpoint allows administrators to manually reset a user's token usage.
    Should be used sparingly and only for legitimate reasons.
    """

    try:
        # Authenticate request (should verify admin permissions)
        await auth_service.authenticate_request(authorization)

        # Perform monthly reset
        success = await subscription_service.perform_monthly_reset(user_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="User not found or reset failed"
            )

        logger.info(f"Admin reset token usage for user {user_id}")

        return {
            "success": True,
            "message": f"Token usage reset successfully for user {user_id}",
            "reset_at": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset usage for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to reset user usage"
        )


async def _ensure_user_exists_locally(user_id: str, shop_id: str):
    """Ensure user exists in local database, sync if needed"""

    from src.database.mongodb import mongodb_client

    # Check if user exists in synced platform data
    platform_user = await mongodb_client.database.platform_users.find_one({
        "user_id": user_id,
        "shop_id": shop_id
    })

    if not platform_user:
        logger.info(f"User {user_id} not found in local data, attempting sync")

        # Try to sync the specific user
        try:
            synced_user = await sync_service.sync_single_user(user_id) if hasattr(sync_service, 'sync_single_user') else None

            if not synced_user:
                logger.warning(f"Failed to sync user {user_id}, creating temporary record")

                # Create minimal user record for subscription
                temp_user_data = {
                    "user_id": user_id,
                    "shop_id": shop_id,
                    "email": f"{user_id}@temp.local",
                    "name": f"User {user_id}",
                    "temporary": True,
                    "created_at": datetime.utcnow(),
                    "sync_method": "subscription_fallback"
                }

                await mongodb_client.database.platform_users.insert_one(temp_user_data)
                logger.info(f"Created temporary user record for {user_id}")

        except Exception as e:
            logger.error(f"Failed to ensure user {user_id} exists locally: {e}")
            # Continue anyway - subscription can work with minimal user data