"""
LLM-Driven Query Processor
This implements the correct flow where the model makes all decisions
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.services.real_model_manager import real_model_manager as model_manager
from src.services.tool_registry import mongodb_tool_registry
from src.utils.json_parser import safe_parse_llm_json

logger = logging.getLogger(__name__)


class LLMQueryProcessor:
    """Query processor that lets the LLM make all decisions"""

    def __init__(self):
        self.tools_schema = self._get_tools_schema()

    def _get_tools_schema(self) -> str:
        """Get schema description of all available tools"""
        return """
Available tools:
1. get_sales_data(start_date, end_date, product, category, shop_id) - Get sales metrics and revenue
2. get_inventory_status(product, category, low_stock_threshold, shop_id) - Check inventory levels
3. get_customer_info(customer_id, include_orders, shop_id) - Get customer details
4. get_order_details(order_id, customer_id, status, start_date, end_date, shop_id) - Get order information
5. get_product_analytics(product, category, start_date, end_date, shop_id) - Product sales performance
6. get_revenue_report(start_date, end_date, group_by, shop_id) - Revenue analysis over time
7. get_product_data(product, category, status, shop_id) - Get product catalog information, count, and prices (status can be "active", "inactive", or omit for all)
"""

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process query using LLM for all decisions"""
        start_time = datetime.utcnow()

        try:
            # Step 1: Let LLM analyze query and decide what tools to call
            tool_selection = await self._llm_select_tools(query, context)

            # Step 2: Execute the tools the LLM selected
            tool_results = []
            for tool_call in tool_selection.get("tools", []):
                result = await mongodb_tool_registry.execute_tool(
                    tool_call["name"],
                    tool_call["parameters"]
                )
                tool_results.append(result)

            # Step 3: Let LLM generate final response with the data
            response = await self._llm_generate_response(query, tool_results)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "success": True,
                "response": response["text"],
                "metadata": {
                    "model_used": model_manager.active_model,
                    "execution_time_ms": int(execution_time),
                    "tools_called": [tc["name"] for tc in tool_selection.get("tools", [])],
                    "query_intent": tool_selection.get("intent", "unknown"),
                    "confidence_score": tool_selection.get("confidence", 0.5),
                    "extracted_entities": [],  # For compatibility
                    "token_usage": response.get("token_usage"),
                    "tokens_per_second": response.get("tokens_per_second")
                },
                "debug": {
                    "tool_calls": tool_selection.get("tools", []),
                    "tool_results": tool_results
                }
            }

        except Exception as e:
            logger.error(f"LLM Query processing error: {e}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error processing your request. Please try again.",
                "error": str(e)
            }

    async def _llm_select_tools(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Let LLM analyze query and select appropriate tools"""

        prompt = f"""You are an e-commerce analytics assistant. Analyze this query and decide which tools to use.

User Query: {query}
Context: Shop ID = {context.get('shop_id', 'unknown')}

{self.tools_schema}

Tool Selection Guide (MATCH THE QUERY KEYWORDS):
- Query contains "sales", "revenue", "earnings", "income" -> use get_sales_data
- Query contains "products" + "how many/count/total/price/cost" -> use get_product_data
- Query contains "inventory", "stock", "warehouse" -> use get_inventory_status
- Query contains "customer", "buyer", "client" -> use get_customer_info
- Query contains "order", "shipment", "delivery" -> use get_order_details
- Query contains "best selling", "top products", "product performance" -> use get_product_analytics
- Query contains "revenue report", "revenue trends" -> use get_revenue_report

IMPORTANT: Match query keywords EXACTLY to the guide above!

Instructions:
1. Analyze the query to understand what the user wants
2. Select the MOST APPROPRIATE tool based on the guide above
3. Return ONLY a JSON object (no explanations before or after)

<json>
{{
    "intent": "sales_inquiry",
    "confidence": 0.9,
    "tools": [
        {{
            "name": "get_sales_data",
            "parameters": {{"shop_id": "{context.get('shop_id', '10')}", "start_date": "2025-09-10", "end_date": "2025-09-17"}}
        }}
    ]
}}
</json>

CRITICAL Rules:
- If query asks about "products" count/price -> MUST use get_product_data, NOT get_sales_data
- DO NOT use wildcards like "*" or "all" for product/category parameters - just omit them
- Output MUST be valid JSON between <json> tags
- Always include shop_id: "{context.get('shop_id', '10')}" in parameters
- For date ranges: last_week = past 7 days from today
- Today's date: {datetime.now().date().isoformat()}
- DO NOT add any text after </json>

JSON:"""

        # Use model to make decision
        if not model_manager.auto_load_best_model(query):
            # Fallback to simple pattern matching if no model
            return self._fallback_tool_selection(query, context)

        try:
            # Increase tokens for complex queries that need multiple tools
            max_tokens = 500 if "comprehensive" in query.lower() else 400
            result = model_manager.inference(prompt, max_tokens=max_tokens, temperature=0.3)

            # Parse JSON response using robust parser
            response_text = result["text"].strip()

            # Use the safe parser that handles mixed JSON/text
            parsed = safe_parse_llm_json(response_text)

            # Check if parsing failed (will have the fallback reasoning)
            if parsed.get("reasoning") == "Failed to parse LLM response":
                logger.warning(f"LLM JSON parsing failed, using fallback. Response preview: {response_text[:200]}")
                return self._fallback_tool_selection(query, context)

            logger.debug(f"Successfully parsed LLM response: intent={parsed.get('intent')}, tools={len(parsed.get('tools', []))}")
            return parsed

        except Exception as e:
            logger.error(f"LLM tool selection error: {e}")
            return self._fallback_tool_selection(query, context)

    async def _llm_generate_response(self, query: str, tool_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """Let LLM generate natural language response using tool results"""

        # Prepare data context
        successful_results = []
        failed_tools = []

        for result in tool_results:
            if result.get("success"):
                successful_results.append({
                    "tool": result.get("tool"),
                    "data": result.get("result")
                })
            else:
                failed_tools.append({
                    "tool": result.get("tool"),
                    "error": result.get("error")
                })

        prompt = f"""You are an e-commerce analytics assistant. Generate a helpful response based on the data.

User Query: {query}

Data Retrieved:
{json.dumps(successful_results, indent=2) if successful_results else "No data successfully retrieved"}

Failed Operations:
{json.dumps(failed_tools, indent=2) if failed_tools else "None"}

CRITICAL Instructions:
- Use ONLY the exact numbers from the data above - DO NOT CHANGE THEM
- For product count: Look for "total_products" field and report that EXACT number
- If "total_products": 107, you MUST say "107 products" NOT any other number
- NEVER count the sample_products array - use total_products field
- If data shows zero or empty, say "no data available"
- Be direct and factual - one sentence is enough

Your response:"""

        try:
            result = model_manager.inference(prompt, max_tokens=150, temperature=0.5)
            return {"text": result["text"].strip()}
        except Exception as e:
            logger.error(f"LLM response generation error: {e}")
            if successful_results:
                return {"text": "I found some data but had trouble formatting the response. Please check the raw results."}
            else:
                return {"text": "I couldn't retrieve the requested data due to a technical issue."}

    def _fallback_tool_selection(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback if LLM is not available"""
        query_lower = query.lower()
        tools = []
        intent = "general"

        # Basic keyword matching as fallback
        if any(word in query_lower for word in ["sales", "revenue", "sold", "earning"]):
            intent = "sales_inquiry"
            tools.append({
                "name": "get_sales_data",
                "parameters": {"shop_id": context.get("shop_id", "10")}
            })
        elif any(word in query_lower for word in ["inventory", "stock", "warehouse"]):
            intent = "inventory_inquiry"
            tools.append({
                "name": "get_inventory_status",
                "parameters": {"shop_id": context.get("shop_id", "10")}
            })
        elif any(word in query_lower for word in ["customer", "buyer", "client"]):
            intent = "customer_inquiry"
            tools.append({
                "name": "get_customer_info",
                "parameters": {"shop_id": context.get("shop_id", "10")}
            })
        elif any(word in query_lower for word in ["product", "item", "performance"]):
            intent = "analytics_inquiry"
            tools.append({
                "name": "get_product_analytics",
                "parameters": {"shop_id": context.get("shop_id", "10")}
            })

        return {
            "intent": intent,
            "confidence": 0.3,  # Low confidence for fallback
            "tools": tools,
            "reasoning": "Fallback pattern matching (LLM not available)"
        }


# Global instance
llm_query_processor = LLMQueryProcessor()