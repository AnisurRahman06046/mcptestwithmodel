# LangChain Integration Documentation

## Overview
This document outlines the integration of LangChain agents to solve token overflow issues and enable complex multi-step query processing in our MongoDB-based analytics system.

## Problem Statement

### Current System Limitations
1. **Token Overflow**: Sending entire datasets (10,000+ items) to LLM exceeds context window (2,048 tokens)
2. **Single-Pass Processing**: Cannot handle queries requiring multiple data fetches
3. **No Complex Calculations**: LLM struggles with mathematical operations on large datasets
4. **No Comparisons**: Cannot compare data across different time periods

### Example Failure
```
Query: "Which products are low on stock?"
Result: 59,082 tokens sent → Model crashes (limit: 2,048)
```

## Solution: LangChain Agent Architecture

### Core Concept
Instead of sending raw data to LLM, use LangChain agents to:
1. **Plan** the execution steps
2. **Execute** data processing with MongoDB
3. **Format** only the results with LLM

## Architecture Design

### Component Overview
```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Router  │──────► Simple queries → Universal LLM Processor
    └────┬────┘
         │
         ▼ Complex queries
┌──────────────────┐
│ LangChain Agent  │
├──────────────────┤
│ • Planning       │
│ • Tool Selection │
│ • Execution      │
└────────┬─────────┘
         │
    ┌────▼────────────────┐
    │   MongoDB Tools      │
    ├──────────────────────┤
    │ • Aggregations       │
    │ • Calculations       │
    │ • Comparisons        │
    └────────┬─────────────┘
             │
        ┌────▼────┐
        │ Results │
        └─────────┘
```

### Tools Definition

#### 1. Data Fetching Tools
```python
- fetch_revenue(period, date_range)
- find_low_stock_products(threshold)
- get_product_statistics(filters)
- fetch_customer_metrics(segment)
```

#### 2. Calculation Tools
```python
- calculate_growth(value1, value2)
- compute_average(data_list)
- aggregate_metrics(data, operation)
```

#### 3. Comparison Tools
```python
- compare_periods(period1, period2, metric)
- rank_products(criteria, limit)
- find_trends(data, timeframe)
```

## Implementation Plan

### Phase 1: Setup and Basic Tools
1. Install LangChain dependencies
2. Create LLM wrapper for local models
3. Implement basic MongoDB tools
4. Create simple agent

### Phase 2: Advanced Features
1. Add complex calculation tools
2. Implement multi-step reasoning
3. Add memory for conversation context
4. Create specialized agents for different domains

### Phase 3: Optimization
1. Implement caching for common queries
2. Add query plan optimization
3. Create tool selection heuristics
4. Add performance monitoring

## Query Flow Examples

### Example 1: Low Stock Query
```
Query: "Which products are low on stock?"

Agent Flow:
1. Thought: Need to find products where stock <= reorder_level
2. Action: find_low_stock_products()
3. Result: 47 products found (returns list)
4. Format: "You have 47 products low on stock..."

Tokens used: ~500 (vs 59,000 in current system)
```

### Example 2: Revenue Comparison
```
Query: "Compare July revenue with June and calculate growth"

Agent Flow:
1. Thought: Need July and June revenue data
2. Action: fetch_revenue(month="July") → $50,000
3. Action: fetch_revenue(month="June") → $45,000
4. Action: calculate_growth(50000, 45000) → 11.1%
5. Format: "Revenue grew by 11.1% from June to July"

Tokens used: ~300
```

### Example 3: Complex Analytics
```
Query: "What's the average price of our top 10 selling products?"

Agent Flow:
1. Thought: Need sales data and product prices
2. Action: get_top_products(limit=10, by="sales")
3. Action: get_product_prices(product_ids=[...])
4. Action: calculate_average(prices)
5. Format: "The average price of top 10 products is $45.67"

Tokens used: ~400
```

## File Structure
```
src/
├── services/
│   ├── langchain_processor.py      # Main LangChain processor
│   ├── mongodb_tools.py            # MongoDB-specific tools
│   ├── calculation_tools.py        # Calculation utilities
│   └── query_router.py             # Routes queries to appropriate processor
├── agents/
│   ├── base_agent.py              # Base agent class
│   ├── analytics_agent.py         # Complex analytics agent
│   └── comparison_agent.py        # Period comparison agent
└── config/
    └── langchain_config.py        # LangChain configuration
```

## Configuration

### Model Configuration
```python
# Use existing local models
model_config = {
    "llm": "qwen2.5-3b",
    "temperature": 0.1,
    "max_tokens": 500
}
```

### Agent Configuration
```python
agent_config = {
    "max_iterations": 5,
    "early_stopping": True,
    "verbose": True,  # For debugging
    "handle_parsing_errors": True
}
```

## Migration Strategy

### Gradual Migration
1. **Week 1**: Implement for "low stock" and "out of stock" queries
2. **Week 2**: Add revenue and sales comparisons
3. **Week 3**: Add complex calculations and trends
4. **Week 4**: Full migration for all complex queries

### Backward Compatibility
- Keep existing `universal_llm_processor` for simple queries
- Route only complex queries to LangChain agent
- Maintain same API response format

## Performance Expectations

### Token Usage Reduction
| Query Type | Current Tokens | With LangChain | Reduction |
|------------|---------------|----------------|-----------|
| Low Stock | 59,000 | 500 | 99% |
| Revenue Comparison | N/A (fails) | 300 | - |
| Top Products | 40,000 | 400 | 99% |

### Query Capabilities
| Feature | Current | LangChain |
|---------|---------|-----------|
| Simple Queries | ✅ | ✅ |
| Large Dataset Processing | ❌ | ✅ |
| Multi-step Reasoning | ❌ | ✅ |
| Comparisons | ❌ | ✅ |
| Complex Calculations | ❌ | ✅ |

## Error Handling

### Agent Error Recovery
```python
try:
    result = agent.run(query)
except TokenLimitError:
    # Fallback to data summarization
    result = agent.run_with_summary(query)
except ToolExecutionError:
    # Retry with different approach
    result = agent.run_alternative(query)
```

## Testing Strategy

### Unit Tests
- Test each tool independently
- Verify MongoDB aggregations
- Test calculation accuracy

### Integration Tests
- Test complete query flows
- Verify agent decision making
- Test error recovery

### Performance Tests
- Measure token usage
- Compare response times
- Test with large datasets

## Monitoring and Debugging

### Logging
```python
# Enable verbose logging for debugging
import langchain
langchain.debug = True

# Log agent decisions
logger.info(f"Agent action: {action}")
logger.info(f"Tool result: {result}")
```

### Metrics to Track
- Token usage per query
- Tool execution time
- Agent iterations
- Success/failure rates

## Success Criteria
1. ✅ No token overflow errors
2. ✅ Handle complex multi-step queries
3. ✅ Accurate calculations on full datasets
4. ✅ Response time < 5 seconds
5. ✅ Natural language responses

## Next Steps
1. Install dependencies
2. Implement basic tools
3. Create simple agent
4. Test with problematic queries
5. Iterate and improve

---

*Document Version: 1.0*
*Date: September 2024*
*Author: System Architecture Team*