# Conversation System - Test Cases

## Test Strategy
Write tests first to ensure no breaking changes and proper conversation functionality.

## Test Categories

### 1. Backward Compatibility Tests (Critical)

#### Test 1.1: Existing Query API Still Works
**Scenario**: Existing clients continue to work without conversation features
```bash
# Test: Query without conversation tracking
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer VALID_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me sales data",
    "options": {}
  }'

# Expected: Same response format as before + new optional conversation fields
Expected Response:
{
  "success": true,
  "response": "Based on your sales data...",
  "structured_data": {...},
  "metadata": {...},
  "user_token_info": {...},
  "subscription_info": {...},
  // NEW OPTIONAL FIELDS (backward compatible):
  "conversation_id": "conv-uuid-123",
  "message_index": 1
}
```

#### Test 1.2: All Existing Endpoints Unchanged
```bash
# Test: All existing endpoints work exactly the same
curl -X GET http://localhost:8000/health/
curl -X GET http://localhost:8000/api/v1/subscription/status -H "Authorization: Bearer JWT"
curl -X GET http://localhost:8000/models/status

# Expected: All return same responses as before
```

### 2. Conversation Creation Tests

#### Test 2.1: First Query Creates Conversation
```bash
# Test: New conversation auto-created on first query
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer VALID_JWT" \
  -d '{
    "query": "Hello, show me my inventory",
    "options": {}
  }'

# Expected Response:
{
  "success": true,
  "response": "Based on your inventory...",
  "conversation_id": "conv-[uuid]",
  "message_index": 1,  // Assistant's response is message 1 (user's was 0)
  // ... other existing fields
}

# Database Verification:
# conversations collection should have:
{
  "conversation_id": "conv-[uuid]",
  "user_id": "1265",
  "shop_id": "10",
  "title": "Hello, show me my inventory",  // Auto-generated from query
  "message_count": 2,  // user + assistant
  "total_tokens_used": [actual_tokens],
  "created_at": [timestamp],
  "status": "active"
}

# conversation_messages collection should have:
[
  {
    "conversation_id": "conv-[uuid]",
    "role": "user",
    "content": "Hello, show me my inventory",
    "message_index": 0,
    "tokens_used": 0,
    "timestamp": [timestamp]
  },
  {
    "conversation_id": "conv-[uuid]",
    "role": "assistant",
    "content": "Based on your inventory...",
    "message_index": 1,
    "tokens_used": [actual_tokens],
    "model_used": "llama-3.1-8b",
    "timestamp": [timestamp]
  }
]
```

#### Test 2.2: Conversation Title Generation
```bash
# Test: Different query lengths generate appropriate titles

# Short query
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Sales"}'
# Expected title: "Sales"

# Medium query
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Show me last month sales data"}'
# Expected title: "Show me last month sales data"

# Long query
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Show me comprehensive detailed analysis of all sales data for the previous quarter including trends"}'
# Expected title: "Show me comprehensive detailed analysis..." (truncated at 50 chars)
```

### 3. Conversation Continuation Tests

#### Test 3.1: Continue Existing Conversation
**Test Setup**: Use conversation_id from Test 2.1 response

```bash
# Test: Second query in same conversation
CONV_ID="conv-uuid-from-previous-test"

curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer VALID_JWT" \
  -d '{
    "query": "What about last week?",
    "conversation_id": "'$CONV_ID'"
  }'

# Expected Response:
{
  "success": true,
  "response": "For last week's data...",
  "conversation_id": "conv-uuid-123",  // Same as before
  "message_index": 3,  // Next message in sequence
  // ... other fields
}

# Database Verification:
# conversations collection updated:
{
  "conversation_id": "conv-uuid-123",
  "message_count": 4,  // Now 4 messages total
  "total_tokens_used": [increased_amount],
  "updated_at": [new_timestamp]
}

# conversation_messages collection has 2 new messages:
[
  // ... previous 2 messages
  {
    "message_index": 2,
    "role": "user",
    "content": "What about last week?"
  },
  {
    "message_index": 3,
    "role": "assistant",
    "content": "For last week's data..."
  }
]
```

#### Test 3.2: Invalid Conversation ID
```bash
# Test: Non-existent conversation ID
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer VALID_JWT" \
  -d '{
    "query": "Test query",
    "conversation_id": "conv-nonexistent-123"
  }'

# Expected Response: 404 Not Found
{
  "error": "CONVERSATION_NOT_FOUND",
  "message": "Conversation not found or access denied"
}
```

#### Test 3.3: Access Control - Other User's Conversation
```bash
# Test: Try to access another user's conversation
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer DIFFERENT_USER_JWT" \
  -d '{
    "query": "Test query",
    "conversation_id": "conv-belongs-to-user1"
  }'

# Expected Response: 403 Forbidden
{
  "error": "ACCESS_DENIED",
  "message": "Conversation not found or access denied"
}
```

### 4. Conversation Management API Tests

#### Test 4.1: List User Conversations
```bash
# Test: Get all conversations for user
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer VALID_JWT"

# Expected Response:
{
  "success": true,
  "conversations": [
    {
      "conversation_id": "conv-uuid-123",
      "title": "Sales Analysis Discussion",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:45:00Z",
      "message_count": 8,
      "total_tokens_used": 1850,
      "last_message_preview": "Based on your data...",
      "status": "active"
    },
    {
      "conversation_id": "conv-uuid-456",
      "title": "Inventory Check",
      "created_at": "2024-01-14T09:15:00Z",
      "updated_at": "2024-01-14T09:20:00Z",
      "message_count": 4,
      "total_tokens_used": 650,
      "last_message_preview": "Your inventory shows...",
      "status": "active"
    }
  ],
  "total_count": 2
}
```

#### Test 4.2: Get Full Conversation History
```bash
# Test: Get complete conversation with all messages
curl -X GET http://localhost:8000/api/v1/conversations/conv-uuid-123 \
  -H "Authorization: Bearer VALID_JWT"

# Expected Response:
{
  "success": true,
  "conversation": {
    "conversation_id": "conv-uuid-123",
    "title": "Sales Analysis Discussion",
    "created_at": "2024-01-15T10:30:00Z",
    "message_count": 4,
    "status": "active"
  },
  "messages": [
    {
      "message_id": "msg-uuid-1",
      "role": "user",
      "content": "Show me sales data",
      "message_index": 0,
      "timestamp": "2024-01-15T10:30:00Z",
      "tokens_used": 0
    },
    {
      "message_id": "msg-uuid-2",
      "role": "assistant",
      "content": "Based on your sales data...",
      "message_index": 1,
      "timestamp": "2024-01-15T10:30:05Z",
      "tokens_used": 245,
      "model_used": "llama-3.1-8b"
    }
    // ... more messages
  ]
}
```

#### Test 4.3: Update Conversation Title
```bash
# Test: Change conversation title
curl -X PUT http://localhost:8000/api/v1/conversations/conv-uuid-123/title \
  -H "Authorization: Bearer VALID_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q1 2024 Sales Analysis"
  }'

# Expected Response:
{
  "success": true,
  "conversation_id": "conv-uuid-123",
  "title": "Q1 2024 Sales Analysis",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

#### Test 4.4: Delete Conversation
```bash
# Test: Delete conversation and all messages
curl -X DELETE http://localhost:8000/api/v1/conversations/conv-uuid-123 \
  -H "Authorization: Bearer VALID_JWT"

# Expected Response:
{
  "success": true,
  "message": "Conversation deleted successfully",
  "deleted_conversation_id": "conv-uuid-123",
  "deleted_messages_count": 8
}

# Database Verification:
# Both conversations and conversation_messages records should be deleted
```

### 5. Integration with Subscription System Tests

#### Test 5.1: Token Usage Tracked Per Conversation
```bash
# Test: Verify tokens from conversation queries are tracked in subscription
# 1. Start with known token usage
curl -X GET http://localhost:8000/api/v1/subscription/status -H "Authorization: Bearer JWT"
# Note current usage: e.g. 1000 tokens

# 2. Make conversation query
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Detailed sales analysis report"}'
# Response shows: "tokens_used": 350

# 3. Check subscription status again
curl -X GET http://localhost:8000/api/v1/subscription/status -H "Authorization: Bearer JWT"
# Expected: current_usage should be 1350 (1000 + 350)

# 4. Verify conversation tracking
curl -X GET http://localhost:8000/api/v1/conversations/CONV_ID -H "Authorization: Bearer JWT"
# Expected: conversation.total_tokens_used should be 350
```

#### Test 5.2: Conversation Blocked When No Subscription
```bash
# Test: User with no subscription cannot create conversations
# 1. Delete user subscription
curl -X DELETE http://localhost:8000/api/v1/subscription -H "Authorization: Bearer JWT"

# 2. Try to start conversation
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Test query"}'

# Expected Response: 402 Payment Required
{
  "error": "NO_SUBSCRIPTION",
  "message": "No active subscription found. Please subscribe first.",
  "subscribe_url": "/api/v1/subscription"
}

# Expected: No conversation or messages created in database
```

### 6. Performance Tests

#### Test 6.1: Large Conversation Handling
```bash
# Test: Conversation with many messages (50+ messages)
# Create conversation with 50 back-and-forth messages
# Verify:
# - All messages stored correctly with proper indexing
# - Conversation retrieval is still fast
# - Message ordering is correct
# - Token totals are accurate
```

#### Test 6.2: Concurrent Conversation Access
```bash
# Test: Multiple users creating conversations simultaneously
# - 10 different users create conversations at the same time
# - Verify no conversation ID collisions
# - Verify proper user isolation
# - Verify database consistency
```

### 7. Data Consistency Tests

#### Test 7.1: Message Ordering
```bash
# Test: Messages are always returned in correct order
# Create conversation with 10 messages
# Retrieve conversation multiple times
# Verify messages always ordered by message_index (0,1,2,3...)
```

#### Test 7.2: Conversation Statistics Accuracy
```bash
# Test: message_count and total_tokens_used are accurate
# Add 5 messages to conversation
# Verify conversation.message_count = 5
# Verify conversation.total_tokens_used = sum of all assistant message tokens
```

### 8. Edge Cases Tests

#### Test 8.1: Very Long Query Content
```bash
# Test: Query with 10,000+ characters
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "VERY_LONG_QUERY_10000_CHARS..."}'

# Expected: Query processed normally, stored completely
# Title generated appropriately (truncated)
```

#### Test 8.2: Special Characters in Content
```bash
# Test: Query with emojis, unicode, special characters
curl -X POST http://localhost:8000/query -H "Authorization: Bearer JWT" \
  -d '{"query": "Show sales 📊 data with 100% accuracy 🎯 for café"}'

# Expected: All characters stored and retrieved correctly
```

#### Test 8.3: Rapid Sequential Queries
```bash
# Test: Send 5 queries in rapid succession to same conversation
# Verify: All messages get correct sequential message_index values
# Verify: No race conditions in message ordering
```

## Test Execution Plan

### Phase 1: Pre-Implementation Testing
- [x] Write all test cases above
- [ ] Create test data fixtures
- [ ] Set up test database collections

### Phase 2: During Implementation Testing
- [ ] Run backward compatibility tests after each change
- [ ] Verify database operations with test data
- [ ] Test API responses match expected formats

### Phase 3: Post-Implementation Testing
- [ ] Full test suite execution
- [ ] Performance testing with realistic data
- [ ] Integration testing with real JWT tokens
- [ ] Load testing with multiple concurrent users

## Success Criteria

✅ **Zero Breaking Changes**: All existing functionality works identically
✅ **Conversation Flow Works**: ChatGPT-like conversation experience
✅ **Data Integrity**: All messages stored and retrieved correctly
✅ **Security**: Users can only access their own conversations
✅ **Performance**: No significant slowdown in query processing
✅ **Subscription Integration**: Token usage tracked properly

Would you like me to implement the test automation scripts for these test cases, or proceed directly to implementation with manual testing?