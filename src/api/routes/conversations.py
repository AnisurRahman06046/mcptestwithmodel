"""
Conversation management API routes.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header

from src.models.api import (
    ConversationListResponse, ConversationDetailResponse,
    ConversationTitleUpdateRequest
)
from src.services.auth_service import auth_service
from src.services.conversation_service import conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    include_archived: bool = False,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    List all conversations for the authenticated user

    Returns conversations sorted by most recent activity first.
    Used to populate the conversation sidebar like in ChatGPT.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Get user's conversations
        conversations = await conversation_service.list_user_conversations(
            context.user_id,
            context.shop_id,
            limit,
            include_archived
        )

        return ConversationListResponse(
            success=True,
            conversations=conversations,
            total_count=len(conversations)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversations"
        )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Get full conversation history with all messages

    Used when user clicks on a conversation in the sidebar to view/continue it.
    Returns all messages in chronological order.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Get conversation with messages
        result = await conversation_service.get_conversation_with_messages(
            conversation_id,
            context.user_id
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or access denied"
            )

        return ConversationDetailResponse(
            success=True,
            conversation=result["conversation"],
            messages=result["messages"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation"
        )


@router.put("/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: ConversationTitleUpdateRequest,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Update conversation title

    Allows users to rename their conversations for better organization.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Update title
        success = await conversation_service.update_conversation_title(
            conversation_id,
            context.user_id,
            request.title
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or access denied"
            )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": request.title,
            "updated_at": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation title: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update conversation title"
        )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Delete conversation and all its messages

    Permanently removes the conversation and all associated messages.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Delete conversation
        result = await conversation_service.delete_conversation(
            conversation_id,
            context.user_id
        )

        if not result["success"]:
            if "not found" in result.get("error", "").lower():
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to delete conversation")
                )

        return {
            "success": True,
            "message": "Conversation deleted successfully",
            "deleted_conversation_id": result["deleted_conversation_id"],
            "deleted_messages_count": result["deleted_messages_count"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation"
        )


@router.patch("/{conversation_id}")
async def update_conversation_status(
    conversation_id: str,
    status: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Update conversation status (archive/unarchive, pin/unpin)

    Allows users to organize their conversations.
    """

    try:
        # Authenticate user
        context = await auth_service.authenticate_request(authorization)

        # Build update query
        update_fields = {"updated_at": datetime.utcnow()}

        if status is not None:
            if status not in ["active", "archived"]:
                raise HTTPException(400, "Invalid status. Must be 'active' or 'archived'")
            update_fields["status"] = status

        if is_pinned is not None:
            update_fields["is_pinned"] = is_pinned

        # Update conversation
        result = await mongodb_client.database.conversations.update_one(
            {
                "conversation_id": conversation_id,
                "user_id": context.user_id,
                "shop_id": context.shop_id
            },
            {"$set": update_fields}
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found or access denied"
            )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "updated_fields": update_fields
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update conversation"
        )