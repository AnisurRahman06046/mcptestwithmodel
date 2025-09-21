# Query Classification System Documentation

## Overview
Production-ready hybrid query classification system that prevents misclassification errors through a multi-layer approach with disambiguation and deterministic fallbacks.

## Problem Statement
- **Issue**: LLM confuses "active products" (status-based) with "products in stock" (inventory-based)
- **Impact**: Returns 0 active products when there are actually 102
- **Root Cause**: Semantic confusion + 40K token payload causing fallback issues

## Solution Architecture

### Layer Overview
```
Query → [Cache] → [Regex] → [Embeddings] → [Disambiguation] → [LLM] → Response
         ↓         ↓          ↓               ↓                ↓
     (0ms/100%) (1ms/95%) (50ms/85%)    (User Input)      (2s/90%)
```

### Classification Layers

#### Layer 1: Cache (0ms, 100% accuracy)
- Stores recent query classifications
- TTL: 5 minutes for factual queries, 1 hour for general
- Implementation: In-memory dict (Phase 1), Redis (Phase 2)

#### Layer 2: Regex Patterns (1ms, 95% confidence)
- Exact pattern matching for high-frequency queries
- Covers ~60% of production queries
- Zero false positives

#### Layer 3: Embeddings (10-50ms, 85% confidence)
- Semantic similarity using sentence-transformers
- Handles paraphrases and synonyms
- Covers additional 20% of queries

#### Layer 4: Disambiguation (User interaction)
- Triggered when confidence < 0.75
- Presents options to user
- Prevents wrong answers

#### Layer 5: LLM Classification (1-2s, 90% confidence)
- Only for truly unknown queries
- Can discover new intents
- Rate-limited to control costs

## Confidence Thresholds

| Method | Confidence | Action |
|--------|------------|--------|
| Regex exact match | 0.95 | Accept immediately |
| Embedding > 0.80 | 0.80-0.95 | Accept |
| Embedding 0.60-0.80 | 0.60-0.80 | Disambiguate |
| LLM > 0.85 | 0.85+ | Accept |
| LLM 0.70-0.85 | 0.70-0.85 | Disambiguate |
| Any < 0.60 | < 0.60 | Fallback to keywords |

## Intent Definitions

### Core Intents

```python
INTENTS = {
    "active_products": {
        "description": "Products with status='active'",
        "patterns": ["active products", "live products", "enabled items"],
        "data_prep": "minimal",
        "token_limit": 2000,
        "use_deterministic": True
    },
    "products_in_stock": {
        "description": "Products with inventory > 0",
        "patterns": ["in stock", "available inventory", "products with quantity"],
        "data_prep": "moderate",
        "token_limit": 10000,
        "use_deterministic": True
    },
    "total_products": {
        "description": "Count of all products",
        "patterns": ["total products", "all products", "product count"],
        "data_prep": "minimal",
        "token_limit": 5000,
        "use_deterministic": True
    },
    "sales_analysis": {
        "description": "Sales and revenue queries",
        "patterns": ["sales", "revenue", "earnings"],
        "data_prep": "full",
        "token_limit": 25000,
        "use_deterministic": False
    }
}
```

## Disambiguation Strategy

When confidence is medium (0.60-0.85), the system asks for clarification:

```json
{
    "needs_clarification": true,
    "confidence": 0.72,
    "question": "I want to make sure I understand correctly. Are you asking about:",
    "options": [
        {
            "id": "1",
            "intent": "active_products",
            "description": "Products with active status (102 products)"
        },
        {
            "id": "2",
            "intent": "products_in_stock",
            "description": "Products with available inventory (0 products)"
        }
    ]
}
```

## Deterministic Processing

For factual queries, bypass LLM entirely:

```python
DETERMINISTIC_QUERIES = {
    "active_products": {
        "db_filter": {"status": "active"},
        "response_template": "You have {count} active products."
    },
    "products_in_stock": {
        "db_filter": {"inventory": {"$gt": 0}},
        "response_template": "You have {count} products in stock."
    },
    "total_products": {
        "db_filter": {},
        "response_template": "You have {count} total products."
    }
}
```

## Implementation Phases

### Phase 1: Quick Fix (Day 1-2)
- [x] Disambiguation for uncertain queries
- [x] Deterministic DB queries for counts
- [x] Basic regex patterns
- [ ] Confidence thresholds

### Phase 2: Intelligence (Week 1-2)
- [ ] Embeddings layer
- [ ] Caching system
- [ ] Extended regex patterns
- [ ] Metrics collection

### Phase 3: Production Hardening (Week 3-4)
- [ ] LLM fallback with rate limiting
- [ ] Learned intent staging
- [ ] Monitoring dashboard
- [ ] A/B testing framework

### Phase 4: Optimization (Month 2-3)
- [ ] Train domain classifier
- [ ] Query decomposition
- [ ] Advanced caching
- [ ] Performance tuning

## API Interface

### Query Classification Request
```python
POST /api/v1/classify
{
    "query": "How many active products do I have?",
    "shop_id": "10",
    "context": {
        "user_id": "user123",
        "session_id": "sess456"
    }
}
```

### Response - High Confidence
```python
{
    "success": true,
    "intent": "active_products",
    "confidence": 0.95,
    "method": "regex",
    "data_requirements": {
        "preparation": "minimal",
        "token_limit": 2000
    }
}
```

### Response - Needs Clarification
```python
{
    "success": true,
    "needs_clarification": true,
    "confidence": 0.65,
    "question": "Please clarify your request:",
    "options": [
        {"id": "1", "intent": "active_products", "description": "Products with active status"},
        {"id": "2", "intent": "products_in_stock", "description": "Products in inventory"}
    ]
}
```

## Monitoring Metrics

### Key Performance Indicators
- **Accuracy**: Target 95%+ for factual queries
- **Latency**: P50 < 50ms, P99 < 500ms
- **Disambiguation Rate**: Target < 5%
- **LLM Fallback Rate**: Target < 10%
- **Cache Hit Rate**: Target > 40%

### Alerts
```python
ALERT_THRESHOLDS = {
    "high_llm_usage": "llm_rate > 20%",
    "high_disambiguation": "disambiguation_rate > 10%",
    "slow_response": "p99_latency > 1000ms",
    "low_confidence": "avg_confidence < 0.80"
}
```

## Error Handling

### Graceful Degradation
1. If embeddings fail → fallback to keywords
2. If LLM times out → use cached or keyword match
3. If DB is slow → return cached if available
4. If all fail → return generic message with support contact

### Rate Limiting
```python
RATE_LIMITS = {
    "llm_calls_per_minute": 10,
    "llm_calls_per_hour": 100,
    "embeddings_per_second": 50
}
```

## Testing Strategy

### Unit Tests
- Each classification layer independently
- Confidence threshold logic
- Disambiguation flow
- Deterministic query handling

### Integration Tests
- Full pipeline flow
- Cache behavior
- Fallback scenarios
- Rate limiting

### Load Tests
- 1000 queries/second target
- Mixed query types
- Cache effectiveness
- Resource usage

## Deployment Checklist

### Prerequisites
- [ ] MongoDB connection configured
- [ ] Redis cache available (Phase 2)
- [ ] Sentence-transformers installed (Phase 2)
- [ ] LLM model loaded
- [ ] Environment variables set

### Configuration
```env
# Classification Settings
CLASSIFICATION_CACHE_TTL=300
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.75
CLASSIFICATION_DISAMBIGUATION_THRESHOLD=0.60

# Rate Limits
LLM_CALLS_PER_HOUR=100
EMBEDDING_CALLS_PER_SECOND=50

# Feature Flags
ENABLE_EMBEDDINGS=false  # Enable in Phase 2
ENABLE_LLM_FALLBACK=false  # Enable in Phase 3
ENABLE_LEARNED_INTENTS=false  # Enable in Phase 3
```

### Rollout Strategy
1. Deploy with feature flags disabled
2. Enable regex classification only
3. Monitor for 24 hours
4. Gradually enable layers:
   - Day 2: Enable disambiguation
   - Day 3: Enable deterministic queries
   - Week 2: Enable embeddings
   - Week 3: Enable LLM fallback

## Maintenance

### Daily Tasks
- Review disambiguation logs
- Check confidence metrics
- Monitor rate limit usage

### Weekly Tasks
- Review new intent discoveries
- Update regex patterns based on logs
- Tune confidence thresholds

### Monthly Tasks
- Retrain embeddings with new examples
- Evaluate classifier accuracy
- Optimize cache strategy

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High disambiguation rate | Ambiguous patterns | Add more specific regex |
| Slow response times | Too many LLM calls | Check cache, add patterns |
| Wrong classifications | Confidence too low | Adjust thresholds |
| Rate limit exceeded | High traffic | Increase limits or add cache |

## Future Enhancements

### Short Term (1-3 months)
- Query decomposition for multi-intent
- Personalized classification per user
- Automatic pattern learning

### Long Term (3-6 months)
- Train custom domain classifier
- Multi-language support
- Voice query support
- Federated learning from all shops

## Contact & Support

- **Technical Issues**: File issue in GitHub
- **Performance Problems**: Check monitoring dashboard
- **Feature Requests**: Submit via product board
- **Emergency**: Page on-call engineer

---

Last Updated: 2025-09-21
Version: 1.0.0
Status: In Development