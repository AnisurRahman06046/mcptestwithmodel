import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from src.services.real_model_manager import real_model_manager as model_manager
from src.services.tool_registry import mongodb_tool_registry

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Processes natural language queries and executes appropriate tools"""
    
    def __init__(self):
        self._token_usage = None  # Track token usage for current query
        self.intent_patterns = {
            "greeting": [
                r"^(hi|hello|hey|good morning|good afternoon|good evening)(\s|$|,|!)",
                r"how are you|how's it going|what's up",
                r"^(greetings|salutations)(\s|$|,|!)",
                r"nice to meet you|pleasure to meet you"
            ],
            "general_conversation": [
                r"^(thank you|thanks|appreciate|grateful)",
                r"^(yes|no|okay|ok|sure|alright)(\s|$|,|!)",
                r"can you help|need help|assistance",
                r"what can you do|what are you|who are you"
            ],
            "sales_inquiry": [
                r"sales?|sold|revenue|earnings?|income",
                r"how (much|many).*(sold|sales?|revenue)",
                r"total (sales?|revenue|earnings?)"
            ],
            "inventory_inquiry": [
                r"inventory|stock|out of stock|low stock",
                r"how (much|many).*(inventory|stock|available)",
                r"(low|out).*(stock|inventory)"
            ],
            "customer_inquiry": [
                r"customers?|clients?|buyers?",
                r"top customers?|best customers?",
                r"customer.*(info|details|data)"
            ],
            "order_inquiry": [
                r"orders?|purchases?",
                r"pending|shipped|fulfilled",
                r"order.*(status|details|info)"
            ],
            "analytics_inquiry": [
                r"analyz|trends?|insights?|reports?",
                r"compare|comparison|vs|versus",
                r"performance|metrics",
                r"which products?|what products?|top products?|best products?",
                r"most profit|highest profit|profitable|profitability",
                r"generated|earned|made.*profit",
                r"this week|last week|this month|last month"
            ]
        }
        
        self.entity_patterns = {
            "time_periods": {
                r"last week": ("last_week", 7),
                r"last month": ("last_month", 30),
                r"this week": ("this_week", 7),
                r"this month": ("this_month", 30),
                r"last (\d+) days?": ("days", None),
                r"past (\d+) (weeks?|months?)": ("period", None)
            },
            "products": [
                r"shirt|t-shirt|tee",
                r"jeans|pants|trousers",
                r"iphone|phone|smartphone",
                r"laptop|computer|macbook",
                r"shoes|sneakers|footwear"
            ],
            "categories": [
                r"electronics?",
                r"clothing|apparel|fashion",
                r"books?",
                r"home|garden",
                r"sports?"
            ]
        }
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main query processing pipeline"""
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Intent classification
            intent = self._classify_intent(query)
            
            # Step 2: Entity extraction
            entities = self._extract_entities(query)
            
            # Step 3: Tool selection and parameter mapping
            tool_calls = self._select_tools(intent, entities, query, context)
            
            # Step 4: Execute tools
            tool_results = []
            for tool_call in tool_calls:
                result = await mongodb_tool_registry.execute_tool(tool_call["tool"], tool_call["parameters"])
                tool_results.append(result)
            
            # Step 5: Generate response using model
            response_text = self._generate_response(query, intent, entities, tool_results)
            
            # Step 6: Structure the response
            structured_data = self._structure_data(tool_results)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Include token usage in metadata if available
            metadata = {
                "model_used": model_manager.active_model if model_manager.active_model else "template-based",
                "execution_time_ms": int(execution_time),
                "tools_called": [tc["tool"] for tc in tool_calls],
                "confidence_score": self._calculate_confidence(intent, entities, tool_results),
                "query_intent": intent,
                "extracted_entities": list(entities.keys()) if entities else []
            }
            
            if self._token_usage:
                metadata["token_usage"] = self._token_usage
            
            return {
                "success": True,
                "response": response_text,
                "structured_data": structured_data,
                "metadata": metadata,
                "debug": {
                    "tool_calls": tool_calls,
                    "tool_results": tool_results
                }
            }
            
        except Exception as e:
            logger.error(f"Query processing error: {e}", exc_info=True)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "success": False,
                "response": "I encountered an error processing your request. Please try rephrasing your question.",
                "error": str(e),
                "metadata": {
                    "execution_time_ms": int(execution_time),
                    "confidence_score": 0.0
                }
            }
    
    def _classify_intent(self, query: str) -> str:
        """Classify the intent of the query"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return "general_inquiry"
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from the query"""
        entities = {}
        query_lower = query.lower()
        
        # Extract time periods
        for pattern, (entity_type, days) in self.entity_patterns["time_periods"].items():
            match = re.search(pattern, query_lower)
            if match:
                entities["time_period"] = entity_type
                if days is None and match.groups():
                    entities["time_value"] = match.group(1)
                else:
                    entities["time_days"] = days
                break
        
        # Extract products
        for pattern in self.entity_patterns["products"]:
            if re.search(pattern, query_lower):
                entities["product"] = re.search(pattern, query_lower).group(0)
                break
        
        # Extract categories
        for pattern in self.entity_patterns["categories"]:
            if re.search(pattern, query_lower):
                entities["category"] = re.search(pattern, query_lower).group(0).title()
                break
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', query)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]
        
        return entities
    
    def _select_tools(self, intent: str, entities: Dict[str, Any], query: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Select appropriate tools and map parameters based on intent and entities"""
        tool_calls = []
        
        # Extract shop_id from context for all tools
        base_params = {}
        if context and context.get('shop_id'):
            base_params['shop_id'] = context['shop_id']
        
        if intent == "sales_inquiry":
            params = base_params.copy()
            if "product" in entities:
                params["product"] = entities["product"]
            if "category" in entities:
                params["category"] = entities["category"]
            if "time_period" in entities:
                params.update(self._map_time_period(entities))
            
            tool_calls.append({"tool": "get_sales_data", "parameters": params})
        
        elif intent == "inventory_inquiry":
            params = base_params.copy()
            if "product" in entities:
                params["product"] = entities["product"]
            if "category" in entities:
                params["category"] = entities["category"]
            if "numbers" in entities:
                params["low_stock_threshold"] = entities["numbers"][0]
            
            tool_calls.append({"tool": "get_inventory_status", "parameters": params})
        
        elif intent == "customer_inquiry":
            params = base_params.copy()
            params["include_orders"] = True
            
            # Check if asking for specific customer info
            if re.search(r"customer.*(id|email)", query.lower()):
                # Would need more sophisticated extraction for actual customer IDs/emails
                pass
            
            tool_calls.append({"tool": "get_customer_info", "parameters": params})
        
        elif intent == "order_inquiry":
            params = base_params.copy()
            
            # Extract order status if mentioned
            statuses = ["pending", "processing", "shipped", "fulfilled", "cancelled"]
            for status in statuses:
                if status in query.lower():
                    params["status"] = status
                    break
            
            if "time_period" in entities:
                params.update(self._map_time_period(entities))
            
            tool_calls.append({"tool": "get_order_details", "parameters": params})
        
        elif intent == "analytics_inquiry":
            params = base_params.copy()
            if "product" in entities:
                params["product"] = entities["product"]
            if "category" in entities:
                params["category"] = entities["category"]
            
            # Add time period if available
            if "time_period" in entities:
                params.update(self._map_time_period(entities))
            
            # Determine if it's product analytics or revenue report
            if re.search(r"product|performance|best|top|profit|which.*products?|what.*products?", query.lower()):
                tool_calls.append({"tool": "get_product_analytics", "parameters": params})
            else:
                tool_calls.append({"tool": "get_revenue_report", "parameters": params})
        
        # Handle greetings and general conversation - no tool calls needed
        if intent in ["greeting", "general_conversation"]:
            return []
        
        # Default fallback - only for business queries
        if not tool_calls and intent not in ["greeting", "general_conversation", "general_inquiry"]:
            tool_calls.append({"tool": "get_sales_data", "parameters": base_params})
        
        return tool_calls
    
    def _map_time_period(self, entities: Dict[str, Any]) -> Dict[str, str]:
        """Map time period entities to date parameters"""
        params = {}
        
        if entities.get("time_period") == "last_week":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            params["start_date"] = start_date.date().isoformat()
            params["end_date"] = end_date.date().isoformat()
        elif entities.get("time_period") == "last_month":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            params["start_date"] = start_date.date().isoformat()
            params["end_date"] = end_date.date().isoformat()
        elif entities.get("time_period") == "this_month":
            end_date = datetime.now()
            start_date = end_date.replace(day=1)
            params["start_date"] = start_date.date().isoformat()
            params["end_date"] = end_date.date().isoformat()
        
        return params
    
    def _generate_response(
        self, 
        query: str, 
        intent: str, 
        entities: Dict[str, Any], 
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Generate natural language response using the model"""
        
        # Handle greetings and general conversation without model
        if intent == "greeting":
            return self._generate_greeting_response(query)
        elif intent == "general_conversation":
            return self._generate_conversational_response(query, entities)
        elif intent == "general_inquiry" and not tool_results:
            return self._generate_help_response()
        
        # For business queries, use model if available
        try:
            if not model_manager.auto_load_best_model(query):
                logger.warning("No suitable model available, using template response")
                return self._generate_template_response(intent, tool_results)
        except Exception as e:
            logger.warning(f"Model auto-loading failed: {e}, using template response")
            return self._generate_template_response(intent, tool_results)
        
        # Create optimized prompt for the model
        prompt = self._create_model_prompt(query, intent, entities, tool_results)
        
        try:
            logger.info(f"Starting model inference with active model: {model_manager.active_model}")
            # Use model manager for generation with shorter max_tokens to reduce inference time
            result = model_manager.inference(prompt, max_tokens=100, temperature=0.3)
            logger.info("Model inference completed successfully")
            
            # Clean up the response text
            response_text = self._clean_model_response(result["text"])
            
            # Store token usage for metadata
            self._token_usage = result["token_usage"]
            
            return response_text
            
        except Exception as e:
            logger.error(f"Model generation error: {e}")
            # Reset token usage on error
            self._token_usage = None
            return self._generate_template_response(intent, tool_results)
    
    def _generate_greeting_response(self, query: str) -> str:
        """Generate natural greeting response"""
        query_lower = query.lower().strip()
        
        if "how are you" in query_lower or "how's it going" in query_lower:
            return "Hello! I'm doing well, thank you for asking. I'm here to help you analyze your e-commerce data. How can I assist you today?"
        elif any(greeting in query_lower for greeting in ["good morning", "good afternoon", "good evening"]):
            return "Good day! I'm ready to help you with your business analytics and data insights. What would you like to know?"
        elif "what's up" in query_lower:
            return "Hello! Not much, just ready to help you dive into your business data. What would you like to explore today?"
        else:
            return "Hello! I'm your e-commerce data assistant. I can help you analyze sales, inventory, customers, orders, and business performance. What would you like to know?"
    
    def _generate_conversational_response(self, query: str, entities: Dict[str, Any]) -> str:
        """Generate natural conversational response"""
        query_lower = query.lower().strip()
        
        if query_lower.startswith(("thank", "thanks", "appreciate")):
            return "You're very welcome! I'm here whenever you need insights about your business data. Feel free to ask me anything about your sales, inventory, customers, or orders."
        elif query_lower in ["yes", "no", "okay", "ok", "sure", "alright"]:
            return "Great! What would you like to explore about your business today? I can analyze sales trends, inventory levels, customer behavior, or order patterns."
        elif "can you help" in query_lower or "need help" in query_lower:
            return "Absolutely! I can help you analyze your e-commerce data. Try asking me about sales performance, inventory status, top customers, recent orders, or business trends."
        elif "what can you do" in query_lower or "what are you" in query_lower:
            return "I'm your e-commerce data analyst! I can help you understand your business performance by analyzing sales data, tracking inventory levels, identifying top customers, monitoring orders, and generating insights to help you make better business decisions."
        else:
            return "I'm here to help with your business analytics. You can ask me about sales, inventory, customers, orders, or any specific business metrics you'd like to explore."
    
    def _generate_help_response(self) -> str:
        """Generate helpful response for general inquiries"""
        return "I'm your e-commerce business analyst. I can help you with:\n• Sales analysis and revenue reports\n• Inventory monitoring and stock alerts\n• Customer insights and top buyer identification\n• Order tracking and fulfillment status\n• Business performance analytics\n\nJust ask me about any aspect of your business data!"
    
    def _create_model_prompt(
        self, 
        query: str, 
        intent: str, 
        entities: Dict[str, Any], 
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Create an optimized prompt for the AI model"""
        
        # Extract successful tool results
        successful_results = [r.get('result', {}) for r in tool_results if r.get('success')]
        
        # Build context based on intent
        context_parts = []
        
        if intent == "sales_inquiry":
            context_parts.append("You are analyzing sales data for an e-commerce business.")
        elif intent == "inventory_inquiry":
            context_parts.append("You are analyzing inventory levels for an e-commerce business.")
        elif intent == "customer_inquiry":
            context_parts.append("You are analyzing customer data for an e-commerce business.")
        elif intent == "order_inquiry":
            context_parts.append("You are analyzing order information for an e-commerce business.")
        else:
            context_parts.append("You are analyzing e-commerce business data.")
        
        # Add data summary
        if successful_results:
            context_parts.append(f"Data available: {json.dumps(successful_results, indent=2)}")
        
        context = "\n".join(context_parts)
        
        # Create the prompt
        prompt = f"""{context}

User Question: {query}

Instructions:
- Answer directly and concisely
- Use specific numbers from the data
- Be conversational but professional
- Focus on actionable insights
- Keep response under 100 words

Answer:"""
        
        return prompt
    
    def _clean_model_response(self, response: str) -> str:
        """Clean up model response"""
        # Remove common model artifacts
        response = response.strip()
        
        # Remove any prompt echoes or instruction repetition
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('User Question:') and not line.startswith('Instructions:'):
                cleaned_lines.append(line)
        
        cleaned_response = ' '.join(cleaned_lines)
        
        # Remove any remaining artifacts
        artifacts = [
            "Answer:", "Response:", "Based on the data:",
            "According to the information provided:",
            "Here is the answer:"
        ]
        
        for artifact in artifacts:
            if cleaned_response.startswith(artifact):
                cleaned_response = cleaned_response[len(artifact):].strip()
        
        return cleaned_response
    
    def _generate_template_response(self, intent: str, tool_results: List[Dict[str, Any]]) -> str:
        """Generate template-based response as fallback"""
        
        if not tool_results or not any(r.get('success') for r in tool_results):
            return "I wasn't able to retrieve the requested data. Please try rephrasing your question or check if the data exists."
        
        successful_result = next(r for r in tool_results if r.get('success'))
        result_data = successful_result.get('result', {})
        
        if intent == "sales_inquiry":
            if 'total_revenue' in result_data:
                return f"Based on your sales data, you generated ${result_data['total_revenue']} in revenue with {result_data.get('total_quantity', 0)} units sold."
            
        elif intent == "inventory_inquiry":
            if 'low_stock_items' in result_data:
                low_stock_count = len(result_data['low_stock_items'])
                if low_stock_count > 0:
                    return f"You have {low_stock_count} products with low stock levels. The most critical items need immediate attention."
                else:
                    return "All your products are currently well-stocked above the minimum threshold."
        
        elif intent == "customer_inquiry":
            if 'customers' in result_data:
                customers = result_data['customers']
                if customers:
                    top_customer = customers[0]
                    return f"Your top customer is {top_customer['name']} with ${top_customer['total_spent']} in total purchases across {top_customer['total_orders']} orders."
        
        elif intent == "order_inquiry":
            if 'summary' in result_data:
                summary = result_data['summary']
                return f"You have {summary['total_orders']} orders with a total value of ${summary['total_value']}. The average order value is ${summary['average_order_value']}."
        
        return "I've retrieved your data successfully. Please review the detailed information provided."
    
    def _prepare_model_context(
        self, 
        query: str, 
        intent: str, 
        entities: Dict[str, Any], 
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Prepare context for model generation"""
        
        context_parts = []
        context_parts.append(f"User asked: {query}")
        context_parts.append(f"Query intent: {intent}")
        
        if entities:
            context_parts.append(f"Extracted entities: {', '.join(f'{k}: {v}' for k, v in entities.items())}")
        
        for result in tool_results:
            if result.get('success'):
                tool_name = result.get('tool', 'unknown')
                context_parts.append(f"Data from {tool_name}: {json.dumps(result.get('result', {}), indent=2)}")
        
        return "\n".join(context_parts)
    
    def _structure_data(self, tool_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Structure the tool results into a consistent format"""
        if not tool_results:
            return {
                "product": None,
                "category": None,
                "period": None,
                "metrics": None,
                "filters": None,
                "results": None
            }
        
        structured = {
            "product": None,
            "category": None,
            "period": None,
            "metrics": None,
            "filters": None,
            "results": None
        }
        
        for result in tool_results:
            if result.get('success'):
                tool_name = result.get('tool')
                result_data = result.get('result', {})
                
                if tool_name == "get_sales_data":
                    structured["metrics"] = {
                        "quantity": result_data.get('total_quantity'),
                        "revenue": result_data.get('total_revenue'),
                        "average_price": result_data.get('average_order_value')
                    }
                    structured["results"] = result_data.get('breakdown', [])
                
                elif tool_name == "get_inventory_status":
                    structured["results"] = {
                        "inventory_summary": {
                            "total_products": result_data.get('total_products'),
                            "low_stock_count": result_data.get('low_stock_count'),
                            "out_of_stock_count": result_data.get('out_of_stock_count')
                        },
                        "critical_items": result_data.get('low_stock_items', [])[:5]
                    }
                
                elif tool_name in ["get_customer_info", "get_order_details", "get_product_analytics", "get_revenue_report"]:
                    # Ensure results is always a list for API validation
                    if isinstance(result_data, dict):
                        structured["results"] = [result_data]
                    elif isinstance(result_data, list):
                        structured["results"] = result_data
                    else:
                        structured["results"] = [{"data": result_data}]
        
        return structured
    
    def _calculate_confidence(
        self, 
        intent: str, 
        entities: Dict[str, Any], 
        tool_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for the response"""
        
        # High confidence for greetings and conversational responses
        if intent in ["greeting", "general_conversation"]:
            return 0.95
        
        # High confidence for help responses
        if intent == "general_inquiry" and not tool_results:
            return 0.9
        
        # For business queries with data
        confidence = 0.5  # Base confidence
        
        # Boost confidence for successful intent classification
        if intent != "general_inquiry":
            confidence += 0.2
        
        # Boost confidence for entity extraction
        if entities:
            confidence += 0.1 * min(len(entities), 3)
        
        # Boost confidence for successful tool execution
        successful_tools = sum(1 for r in tool_results if r.get('success'))
        if successful_tools > 0:
            confidence += 0.2 * min(successful_tools, 2)
        
        # Penalize for tool failures
        failed_tools = sum(1 for r in tool_results if not r.get('success'))
        confidence -= 0.1 * failed_tools
        
        return min(max(confidence, 0.0), 1.0)


# Global query processor instance
query_processor = QueryProcessor()