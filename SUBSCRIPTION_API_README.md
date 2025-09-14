# MCP Server - Subscription & Token Management APIs

## Overview

APIs for subscription management and token usage tracking in the MCP Server.

## Database Collections

### New Collections
- `subscriptions` - User subscription data
- `token_usage` - Token usage tracking

### Existing Collections
- `platform_users` - Synced user data (existing)

## API Endpoints

### 1. Create/Update Subscription
```http
POST /api/v1/subscription
Authorization: Bearer <jwt_token>
```

**Request:**
```json
{
  "plan_name": "pro",
  "allocated_tokens": 20000,
  "monthly_fee": 29.99,
  "currency": "USD"
}
```

**Response:**
```json
{
  "success": true,
  "subscription_id": "65f1a2b3c4d5e6f7a8b9c0d1",
  "user_id": "user123",
  "allocated_tokens": 20000,
  "current_usage": 0,
  "remaining_tokens": 20000,
  "status": "active"
}
```

### 2. Get Subscription Status
```http
GET /api/v1/subscription/status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "plan_name": "pro",
  "allocated_tokens": 20000,
  "current_usage": 12750,
  "remaining_tokens": 7250,
  "usage_percentage": 63.75,
  "monthly_fee": 29.99,
  "status": "active"
}
```

### 3. Process Query (Enhanced)
```http
POST /api/v1/query
Authorization: Bearer <jwt_token>
```

**Request:**
```json
{
  "query": "Show me sales data",
  "options": {}
}
```

**Response (Enhanced with token info):**
```json
{
  "success": true,
  "response": "Based on your sales data...",
  "metadata": {
    "token_usage": {
      "total_tokens": 239
    }
  },
  "user_token_info": {
    "used_this_query": 239,
    "total_used": 12989,
    "remaining": 7011
  }
}
```

## Error Responses

### No Subscription
```json
{
  "success": false,
  "error": "NO_SUBSCRIPTION",
  "message": "No active subscription found"
}
```

### Token Limit Exceeded
```json
{
  "success": false,
  "error": "TOKEN_LIMIT_EXCEEDED",
  "message": "Monthly token limit exceeded",
  "current_usage": 20150,
  "allocated_tokens": 20000
}
```

## Implementation Flow

1. **User Subscribes**: Platform → POST `/api/v1/subscription`
2. **User Queries**: Platform → POST `/api/v1/query` (checks limits)
3. **Show Stats**: Platform → GET `/api/v1/subscription/status`

## HTTP Status Codes

- `200` - Success
- `401` - Invalid JWT
- `402` - No subscription
- `429` - Token limit exceeded
- `500` - Server error