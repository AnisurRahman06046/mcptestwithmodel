"""
Conversation management service for handling chat history like ChatGPT.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.database.mongodb import mongodb_client
from src.models.mongodb_models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing ChatGPT-style conversations"""

    async def create_conversation(
        self,
        user_id: str,
        shop_id: str,
        first_query: str
    ) -> Conversation:
        """Create a new conversation (like opening new chat in ChatGPT)"""

        try:
            # Generate title from first query
            title = self._generate_title(first_query)

            # Create conversation record
            conversation = Conversation(
                user_id=user_id,
                shop_id=shop_id,
                title=title,
                message_count=0,
                total_tokens_used=0,
                status="active"
            )

            # Insert into database
            await mongodb_client.database.conversations.insert_one(
                conversation.model_dump(by_alias=True)
            )

            logger.info(f"Created new conversation {conversation.conversation_id} for user {user_id}")
            return conversation

        except Exception as e:
            logger.error(f"Failed to create conversation for user {user_id}: {e}", exc_info=True)
            raise e

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation by ID (with access control)"""

        try:
            conversation = await mongodb_client.database.conversations.find_one({
                "conversation_id": conversation_id,
                "user_id": user_id,  # Access control
                "status": {"$in": ["active", "archived"]}
            })

            return conversation

        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tokens_used: int = 0,
        execution_time_ms: int = 0,
        model_used: Optional[str] = None,
        structured_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> ConversationMessage:
        """Add message to conversation (user or assistant message)"""

        try:
            # Get current conversation to determine message index
            conversation = await mongodb_client.database.conversations.find_one({
                "conversation_id": conversation_id
            })

            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            message_index = conversation["message_count"]

            # Create message
            message = ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_index=message_index,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                model_used=model_used,
                structured_data=structured_data,
                metadata=metadata or {}
            )

            # Insert message
            await mongodb_client.database.conversation_messages.insert_one(
                message.model_dump(by_alias=True)
            )

            # Update conversation statistics
            await mongodb_client.database.conversations.update_one(
                {"conversation_id": conversation_id},
                {
                    "$inc": {
                        "message_count": 1,
                        "total_tokens_used": tokens_used
                    },
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            logger.info(f"Added {role} message to conversation {conversation_id}, index {message_index}")
            return message

        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}", exc_info=True)
            raise e

    async def get_conversation_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""

        try:
            # Verify user owns conversation
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return []

            # Get messages ordered by message_index
            query = {"conversation_id": conversation_id, "status": "active"}
            cursor = mongodb_client.database.conversation_messages.find(query).sort("message_index", 1)

            if limit:
                cursor = cursor.limit(limit)

            messages = await cursor.to_list(length=None)

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    async def list_user_conversations(
        self,
        user_id: str,
        shop_id: str,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List all conversations for a user"""

        try:
            # Build query
            query = {"user_id": user_id, "shop_id": shop_id}
            if not include_archived:
                query["status"] = "active"

            # Get conversations sorted by updated_at (most recent first)
            conversations = await mongodb_client.database.conversations.find(query).sort("updated_at", -1).limit(limit).to_list(length=None)

            # Add last message preview for each conversation
            for conv in conversations:
                last_message = await mongodb_client.database.conversation_messages.find_one(
                    {"conversation_id": conv["conversation_id"], "role": "assistant"},
                    sort=[("message_index", -1)]
                )

                if last_message:
                    preview = last_message["content"][:100]
                    conv["last_message_preview"] = preview + "..." if len(last_message["content"]) > 100 else preview
                else:
                    conv["last_message_preview"] = "No messages yet"

            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations for user {user_id}: {e}")
            return []

    async def update_conversation_title(
        self,
        conversation_id: str,
        user_id: str,
        new_title: str
    ) -> bool:
        """Update conversation title"""

        try:
            result = await mongodb_client.database.conversations.update_one(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,  # Access control
                    "status": {"$in": ["active", "archived"]}
                },
                {
                    "$set": {
                        "title": new_title,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            success = result.modified_count > 0
            if success:
                logger.info(f"Updated title for conversation {conversation_id}")
            else:
                logger.warning(f"No conversation updated for {conversation_id} (user {user_id})")

            return success

        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")
            return False

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Delete conversation and all its messages"""

        try:
            # Verify ownership
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return {"success": False, "error": "Conversation not found"}

            # Delete all messages
            messages_result = await mongodb_client.database.conversation_messages.delete_many({
                "conversation_id": conversation_id
            })

            # Delete conversation
            conv_result = await mongodb_client.database.conversations.delete_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })

            if conv_result.deleted_count > 0:
                logger.info(f"Deleted conversation {conversation_id} and {messages_result.deleted_count} messages")
                return {
                    "success": True,
                    "deleted_conversation_id": conversation_id,
                    "deleted_messages_count": messages_result.deleted_count
                }
            else:
                return {"success": False, "error": "Failed to delete conversation"}

        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return {"success": False, "error": str(e)}

    def _generate_title(self, query: str) -> str:
        """Generate conversation title from first query"""

        # Take first 50 characters, clean up
        title = query.strip()

        if len(title) > 50:
            # Find last complete word within 50 chars
            truncated = title[:50]
            last_space = truncated.rfind(' ')
            if last_space > 20:  # Ensure minimum length
                title = truncated[:last_space] + "..."
            else:
                title = truncated + "..."

        return title

    async def get_conversation_with_messages(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation with all messages (for full history view)"""

        try:
            # Get conversation
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return None

            # Get all messages
            messages = await self.get_conversation_messages(conversation_id, user_id)

            return {
                "conversation": conversation,
                "messages": messages
            }

        except Exception as e:
            logger.error(f"Failed to get conversation with messages {conversation_id}: {e}")
            return None


# Global conversation service instance
conversation_service = ConversationService()