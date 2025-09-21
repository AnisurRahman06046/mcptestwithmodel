"""
Universal LLM Query Processor
Uses the universal query builder to fetch complete datasets,
then processes them with LLM to answer any query
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.services.real_model_manager import real_model_manager as model_manager
from src.services.universal_query_builder import universal_query_builder
from src.utils.json_parser import safe_parse_llm_json

logger = logging.getLogger(__name__)


class UniversalLLMProcessor:
    """
    Universal query processor that:
    1. Identifies required domains
    2. Fetches complete datasets
    3. Uses LLM to process and answer queries
    """

    def __init__(self):
        self.domain_keywords = {
            "products": ["product", "item", "catalog", "sku", "price", "cost", "expensive", "cheap", "category", "brand"],
            "sales": ["sales", "revenue", "sold", "earning", "income", "profit", "transaction", "performance", "order", "orders", "today", "yesterday", "week", "month"],
            "inventory": ["inventory", "stock", "warehouse", "available", "quantity", "reorder", "low stock"],
            "customers": ["customer", "buyer", "client", "user", "member", "loyalty", "vip"],
            "orders": ["order", "purchase", "shipment", "delivery", "payment", "checkout", "cart"]
        }

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process any query using universal data fetching and LLM processing
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Identify which domains are needed
            domains_needed = await self._identify_domains(query)
            logger.info(f"Domains identified for query: {domains_needed}")

            # If no domains are needed (e.g., greeting), handle it directly
            if not domains_needed:
                logger.info("No domains needed - handling as conversational query")
                return await self._handle_conversational_query(query)

            # Step 2: Extract date range using LLM (handles ANY date expression)
            date_range = await self._llm_extract_date_range(query)
            if date_range:
                logger.info(f"LLM extracted date range: {date_range}")
            else:
                logger.warning(f"LLM failed to extract date from query: {query}")
                # Fallback to pattern matching for common expressions
                date_range = self._extract_date_range(query)
                if date_range:
                    logger.info(f"Pattern extracted date range: {date_range}")
                else:
                    logger.warning(f"No date range found in query: {query}")

            # Step 3: Fetch complete datasets for all needed domains
            all_data = {}
            for domain in domains_needed:
                logger.info(f"Fetching complete {domain} data...")
                domain_data = await universal_query_builder.fetch_domain_data(
                    domain=domain,
                    shop_id=context.get("shop_id", "10"),
                    date_range=date_range
                )
                if domain_data.get("success"):
                    all_data[domain] = domain_data["data"]
                    logger.info(f"Fetched {domain} data successfully")

            # Step 4: Use LLM to process the data and answer the query
            final_answer = await self._process_with_llm(query, all_data)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "success": True,
                "response": final_answer["answer"],
                "structured_data": final_answer.get("structured_data"),
                "metadata": {
                    "model_used": model_manager.active_model,
                    "execution_time_ms": int(execution_time),
                    "tools_called": list(all_data.keys()),
                    "query_intent": final_answer.get("intent", "general"),
                    "confidence_score": final_answer.get("confidence", 0.9),
                    "extracted_entities": [],
                    "token_usage": final_answer.get("token_usage"),
                    "tokens_per_second": final_answer.get("tokens_per_second")
                },
                "debug": {
                    "domains_fetched": list(all_data.keys()),
                    "date_range": date_range,
                    "data_statistics": {
                        domain: data.get("statistics", {})
                        for domain, data in all_data.items()
                    }
                }
            }

        except Exception as e:
            logger.error(f"Universal query processing error: {e}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error processing your request. Please try again.",
                "error": str(e)
            }

    async def _identify_domains(self, query: str) -> List[str]:
        """
        Use LLM to identify which domains are needed (more flexible than keywords)
        """
        prompt = f"""You are a domain classifier. Identify data domains needed for this query.

Query: "{query}"

Available domains: products, sales, inventory, customers, orders

IMPORTANT: If the query is a greeting (hi, hello, hey, etc.) or general conversation that doesn't ask for specific data, return an empty array [].

Return ONLY a JSON array of domain names. No explanations.

Examples:
"How many products?" → ["products"]
"July revenue" → ["sales"]
"Best selling products" → ["products", "sales"]
"Hi" → []
"Hello there" → []
"How are you?" → []
"Thank you" → []

Now classify the query above:"""

        try:
            if model_manager.auto_load_best_model(query):
                result = model_manager.inference(prompt, max_tokens=50, temperature=0.0)
                # Try to parse as JSON array
                text = result.get("text", "").strip()
                if text.startswith("[") and text.endswith("]"):
                    import json
                    domains = json.loads(text)
                    if domains and isinstance(domains, list):
                        logger.info(f"LLM identified domains: {domains}")
                        return domains
        except Exception as e:
            logger.warning(f"LLM domain identification failed: {e}, using keyword fallback")

        # Fallback to keyword-based identification
        query_lower = query.lower()
        domains = []

        for domain, keywords in self.domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                domains.append(domain)

        if not domains:
            domains.append("products")  # Default fallback

        return list(set(domains))

    async def _llm_extract_date_range(self, query: str) -> Optional[Dict[str, str]]:
        """
        Use LLM to extract date range from natural language (handles ANY date expression)
        """
        today = datetime.now().date().isoformat()
        current_year = datetime.now().year

        prompt = f"""You are a date extraction system. Extract date range from the query.
Today is {today}.

Query: "{query}"

If the query mentions a date/time period, return ONLY a JSON object with start and end dates.
If no date is mentioned, return ONLY the word: null

CRITICAL: Return ONLY the JSON or null. No explanations, no text, no formatting.

Examples:
Input: "revenue in July"
Output: {{"start": "{current_year}-07-01", "end": "{current_year}-07-31"}}

Input: "How many products do we have?"
Output: null

Input: "sales last month"
Output: {{"start": "{(datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).date().isoformat()}", "end": "{(datetime.now().replace(day=1) - timedelta(days=1)).date().isoformat()}"}}

Now extract date from the query above. Return ONLY JSON or null:"""

        try:
            if model_manager.auto_load_best_model(query):
                # Use temperature 0 for deterministic output
                result = model_manager.inference(prompt, max_tokens=50, temperature=0.0)
                text = result.get("text", "").strip()
                logger.debug(f"LLM date extraction raw response: {text}")

                # Clean up the response - remove any extra text
                # Sometimes LLMs add text before/after JSON
                if text and text != "null":
                    # Try to extract JSON from the response
                    import json
                    import re

                    # Look for JSON pattern in the text
                    json_match = re.search(r'\{[^}]+\}', text)
                    if json_match:
                        try:
                            date_range = json.loads(json_match.group())
                            if "start" in date_range and "end" in date_range:
                                logger.info(f"LLM successfully extracted dates: {date_range}")
                                return date_range
                            else:
                                logger.warning(f"LLM response missing start/end: {date_range}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON from LLM response: {text}, error: {e}")
                    else:
                        logger.warning(f"No JSON found in LLM response: {text}")
                else:
                    logger.debug("LLM returned null or empty for date extraction")
            else:
                logger.warning("Failed to load model for date extraction")
        except Exception as e:
            logger.error(f"LLM date extraction failed with error: {e}", exc_info=True)

        return None

    def _extract_date_range(self, query: str) -> Optional[Dict[str, str]]:
        """
        Extract date range from query - fallback for when LLM fails
        """
        query_lower = query.lower()
        today = datetime.now().date()
        current_year = datetime.now().year

        # Check for month names first
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }

        for month_name, month_num in months.items():
            if month_name in query_lower:
                # Get the first and last day of the month
                from calendar import monthrange
                first_day = datetime(current_year, month_num, 1).date()
                last_day = datetime(current_year, month_num, monthrange(current_year, month_num)[1]).date()

                logger.info(f"Pattern matcher found month '{month_name}', returning {first_day} to {last_day}")
                return {
                    "start": first_day.isoformat(),
                    "end": last_day.isoformat()
                }

        # Common date patterns
        if "today" in query_lower:
            return {
                "start": today.isoformat(),
                "end": today.isoformat()
            }
        elif "yesterday" in query_lower:
            yesterday = today - timedelta(days=1)
            return {
                "start": yesterday.isoformat(),
                "end": yesterday.isoformat()
            }
        elif "this week" in query_lower:
            # This week: Last 7 days including today
            week_start = today - timedelta(days=6)
            return {
                "start": week_start.isoformat(),
                "end": today.isoformat()
            }
        elif "last week" in query_lower or "past week" in query_lower:
            week_ago = today - timedelta(days=7)
            return {
                "start": week_ago.isoformat(),
                "end": today.isoformat()
            }
        elif "last month" in query_lower or "past month" in query_lower:
            month_ago = today - timedelta(days=30)
            return {
                "start": month_ago.isoformat(),
                "end": today.isoformat()
            }
        elif "last year" in query_lower or "past year" in query_lower:
            year_ago = today - timedelta(days=365)
            return {
                "start": year_ago.isoformat(),
                "end": today.isoformat()
            }
        elif "this month" in query_lower:
            first_day = today.replace(day=1)
            return {
                "start": first_day.isoformat(),
                "end": today.isoformat()
            }

        # Default: No specific date range
        return None

    async def _process_with_llm(self, query: str, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to process the complete datasets and answer the query
        """
        query_lower = query.lower()

        # Intelligently prepare data based on query type to avoid token limits
        if "active" in query_lower and "product" in query_lower:
            # For active products queries, only send essential data
            full_data_for_llm = self._prepare_minimal_data_for_active_products(all_data)
        elif "categor" in query_lower:
            # For category queries, include all categories
            full_data_for_llm = self._prepare_category_focused_data(all_data)
        else:
            # Get full data for other queries
            full_data_for_llm = self._prepare_full_data_for_llm(all_data)

        # Log the size of data being sent
        import sys
        data_str = json.dumps(full_data_for_llm, indent=2, default=str)
        data_size = sys.getsizeof(data_str)
        estimated_tokens = len(data_str) // 4  # Rough estimate: 4 chars per token
        logger.info(f"Sending data to LLM - Size: {data_size} bytes, Estimated tokens: {estimated_tokens}")

        if estimated_tokens > 10000:  # Reduced from 30000 to ensure LLM can process
            logger.warning(f"Data too large ({estimated_tokens} tokens), using fallback")
            # Pass the prepared data with product_status_distribution to fallback
            return self._create_enhanced_fallback(query, all_data, full_data_for_llm)

        prompt = f"""Analyze the data and answer the query with a natural language response. Return ONLY JSON, no explanations.

Query: {query}

Data:
{json.dumps(full_data_for_llm, indent=2, default=str)}

INSTRUCTIONS FOR ANSWERING:

1. READ THE QUERY CAREFULLY - Answer what is actually being asked, not what you assume

2. For listing items (e.g., "list 5 categories", "show me products"):
   - Extract and list the requested items from the data
   - Look at actual product data to find unique categories, names, etc.
   - Format as a numbered list or bullet points as appropriate

3. For counting queries:
   - "active products": Use product_status_distribution.active
   - "products in stock": Use statistics.products_in_stock
   - "total products": Use statistics.total_products

4. For sales/revenue:
   - Use statistics.total_revenue and statistics.total_orders

5. For category-related queries:
   - For "total categories" or "how many categories": Use statistics.total_categories (from category collection)
   - For listing categories: Use the categories array or unique_categories
   - Note: statistics.total_categories is the authoritative count

ANSWER FORMAT:
- Be conversational and natural
- For lists: Use numbered or bullet format
- For counts: Include units (e.g., "102 active products")
- For zero: Say "You don't have any..." instead of "0"

Return ONLY this JSON:
{{
    "answer": "your natural language answer here",
    "intent": "listing or counting or sales_inquiry or product_inquiry or other",
    "confidence": 0.9
}}"""

        try:
            # Load the best model for processing
            if not model_manager.auto_load_best_model(query):
                logger.warning("No model available, using fallback")
                return self._create_fallback_answer(query, all_data)

            logger.info(f"Processing query with LLM: {query}")
            logger.debug(f"Data domains available: {list(all_data.keys())}")

            result = model_manager.inference(prompt, max_tokens=500, temperature=0.3)

            # Parse the response
            response_text = result.get("text", "")
            logger.debug(f"LLM raw response: {response_text[:500]}")

            parsed = safe_parse_llm_json(response_text)
            logger.debug(f"Parsed response: {parsed}")

            if not parsed.get("answer") or parsed.get("answer") == "I found the following information: ":
                logger.warning("LLM failed to provide proper answer, using enhanced fallback")
                return self._create_enhanced_fallback(query, all_data, full_data_for_llm)

            return {
                "answer": parsed["answer"],
                "intent": parsed.get("intent", "general"),
                "confidence": parsed.get("confidence", 0.9),
                "structured_data": parsed.get("structured_data"),
                "token_usage": result.get("token_usage"),
                "tokens_per_second": result.get("tokens_per_second")
            }

        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            return self._create_fallback_answer(query, all_data)

    def _create_data_summary(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of available data for the prompt
        """
        summary = {}

        for domain, data in all_data.items():
            domain_summary = {
                "statistics": data.get("statistics", {}),
                "data_available": []
            }

            # List what data is available
            for key in data.keys():
                if key != "statistics":
                    if isinstance(data[key], list):
                        domain_summary["data_available"].append(f"{key} ({len(data[key])} items)")
                    elif isinstance(data[key], dict):
                        domain_summary["data_available"].append(f"{key} (dict)")
                    else:
                        domain_summary["data_available"].append(key)

            summary[domain] = domain_summary

        return summary

    def _prepare_category_focused_data(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data focused on categories for category-related queries
        """
        prepared = {}

        for domain, data in all_data.items():
            if domain == "products":
                domain_data = {
                    "statistics": data.get("statistics", {})
                }

                # Include ALL categories for category queries
                domain_data["categories"] = data.get("categories", [])

                # Get unique categories from products
                all_products = data.get("products", [])
                unique_categories = set()
                category_product_count = {}

                for prod in all_products:
                    category = prod.get("category")
                    if category:
                        unique_categories.add(category)
                        category_product_count[category] = category_product_count.get(category, 0) + 1

                domain_data["unique_categories"] = list(unique_categories)
                domain_data["category_product_counts"] = category_product_count
                domain_data["total_unique_categories"] = len(unique_categories)

                # IMPORTANT: Ensure statistics.total_categories is set correctly
                if "statistics" not in domain_data:
                    domain_data["statistics"] = {}
                domain_data["statistics"]["total_categories"] = len(data.get("categories", []))

                # Log the actual counts for debugging
                logger.info(f"Category data prepared - Collection count: {len(data.get('categories', []))}, "
                           f"Unique from products: {len(unique_categories)}")

                # Include a few sample products per category (max 2 per category)
                samples_by_category = {}
                for prod in all_products[:50]:  # Look at first 50 products for samples
                    category = prod.get("category")
                    if category:
                        if category not in samples_by_category:
                            samples_by_category[category] = []
                        if len(samples_by_category[category]) < 2:
                            samples_by_category[category].append({
                                "name": prod.get("name"),
                                "sku": prod.get("sku"),
                                "price": prod.get("price")
                            })

                domain_data["sample_products_by_category"] = samples_by_category
                prepared[domain] = domain_data
            else:
                prepared[domain] = {"statistics": data.get("statistics", {})}

        return prepared

    def _prepare_minimal_data_for_active_products(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare minimal data specifically for active products queries to avoid token limits
        """
        prepared = {}

        for domain, data in all_data.items():
            if domain == "products":
                # Only include essential data for active products query
                all_products = data.get("products", [])

                # Count status distribution
                status_counts = {}
                for prod in all_products:
                    status = str(prod.get("status", "unknown")).lower()
                    status_counts[status] = status_counts.get(status, 0) + 1

                prepared[domain] = {
                    "statistics": data.get("statistics", {}),
                    "product_status_distribution": status_counts,
                    "ACTIVE_PRODUCTS_COUNT": status_counts.get("active", 0),
                    "total_products": len(all_products),
                    "NOTE": "Use ACTIVE_PRODUCTS_COUNT for 'active products' queries"
                }

        return prepared

    def _prepare_full_data_for_llm(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare full datasets for LLM processing
        Limit size to prevent token overflow
        """
        prepared = {}

        for domain, data in all_data.items():
            domain_data = {
                "statistics": data.get("statistics", {})
            }

            # Include key data based on domain
            if domain == "products":
                # IMPORTANT: Minimize data to avoid token limit (was causing fallback at 39k tokens)
                all_products = data.get("products", [])

                # Only include 3 sample products to show structure (was 500!)
                domain_data["sample_products"] = all_products[:3] if all_products else []
                domain_data["all_products_count"] = len(all_products)

                # Add product status distribution with clear labeling
                if all_products:
                    status_counts = {}
                    for prod in all_products:
                        status = str(prod.get("status", "unknown")).lower()
                        status_counts[status] = status_counts.get(status, 0) + 1
                    domain_data["product_status_distribution"] = status_counts

                    # Add explicit active products count for clarity
                    domain_data["ACTIVE_PRODUCTS_COUNT"] = status_counts.get("active", 0)
                    domain_data["IMPORTANT_NOTE"] = "ACTIVE_PRODUCTS_COUNT is for 'active products' queries"

                # Drastically reduce other data to stay under token limit
                domain_data["skus"] = data.get("skus", [])[:5]  # Was 100, now just 5 samples
                domain_data["categories"] = data.get("categories", [])[:5]  # Was 20
                domain_data["brands"] = data.get("brands", [])[:5]  # Was 20
                if "product_sales" in data:
                    domain_data["product_sales"] = data["product_sales"][:20]

            elif domain == "sales":
                # Include order summaries
                domain_data["daily_sales"] = data.get("daily_sales", [])[:30]
                domain_data["order_items"] = data.get("order_items", [])[:500]
                domain_data["customer_purchases"] = data.get("customer_purchases", [])[:100]

            elif domain == "inventory":
                domain_data["inventory"] = data.get("inventory", [])[:500]
                domain_data["low_stock_items"] = data.get("low_stock_items", [])[:50]
                domain_data["out_of_stock_items"] = data.get("out_of_stock_items", [])[:50]

            elif domain == "customers":
                domain_data["customers"] = data.get("customers", [])[:200]
                domain_data["vip_customers"] = data.get("vip_customers", [])[:50]

            elif domain == "orders":
                domain_data["recent_orders"] = data.get("orders", [])[:200]
                domain_data["status_counts"] = data.get("statistics", {}).get("status_counts", {})

            prepared[domain] = domain_data

        return prepared

    def _create_fallback_answer(self, query: str, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a fallback answer when LLM processing fails
        """
        # Prepare data first to get product_status_distribution
        prepared_data = self._prepare_full_data_for_llm(all_data)
        return self._create_enhanced_fallback(query, all_data, prepared_data)

    async def _handle_conversational_query(self, query: str) -> Dict[str, Any]:
        """
        Handle conversational queries like greetings without fetching data
        """
        prompt = f"""You are a helpful assistant for an e-commerce platform. Respond naturally to this query.

Query: "{query}"

Provide a friendly, helpful response. Be concise but warm.

Return your response as JSON with the following structure:
{{
    "answer": "Your natural language response here",
    "intent": "greeting/help/general",
    "confidence": 0.95
}}"""

        try:
            if model_manager.auto_load_best_model(query):
                result = model_manager.inference(prompt, max_tokens=100, temperature=0.7)
                response_text = result.get("text", "").strip()

                # Try to parse as JSON
                try:
                    import json
                    response_json = json.loads(response_text)
                    return {
                        "answer": response_json.get("answer", "Hello! How can I help you today?"),
                        "intent": response_json.get("intent", "general"),
                        "confidence": response_json.get("confidence", 0.95),
                        "token_usage": result.get("usage"),
                        "tokens_per_second": result.get("tokens_per_second")
                    }
                except:
                    # Fallback if JSON parsing fails
                    return {
                        "answer": "Hello! How can I help you today?",
                        "intent": "greeting",
                        "confidence": 0.95
                    }
            else:
                # Fallback response if model can't load
                return {
                    "answer": "Hello! How can I help you today?",
                    "intent": "greeting",
                    "confidence": 0.95
                }
        except Exception as e:
            logger.error(f"Error handling conversational query: {e}")
            return {
                "answer": "Hello! How can I help you today?",
                "intent": "greeting",
                "confidence": 0.95
            }

    def _create_enhanced_fallback(self, query: str, all_data: Dict[str, Any], prepared_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an enhanced fallback answer using a simplified LLM prompt when full data is too large
        """
        query_lower = query.lower()
        logger.info(f"Using enhanced fallback for query: {query}")

        # Use prepared_data if available, otherwise prepare it
        if prepared_data is None:
            prepared_data = self._prepare_full_data_for_llm(all_data)

        # First, try to use LLM with just statistics for natural language response
        try:
            # For active products queries, include the product_status_distribution
            stats_summary = {}
            for domain, data in all_data.items():
                if "statistics" in data:
                    stats_summary[domain] = data["statistics"]

            # Add product_status_distribution from prepared_data if available
            if "active" in query_lower and "product" in query_lower:
                if "products" in prepared_data and "product_status_distribution" in prepared_data["products"]:
                    stats_summary["product_status_distribution"] = prepared_data["products"]["product_status_distribution"]
                    logger.info(f"Added product_status_distribution to stats: {stats_summary['product_status_distribution']}")

            # Create a simplified prompt with just statistics
            stats_prompt = f"""Answer this query with a complete, natural language response.

Query: {query}

Available Statistics:
{json.dumps(stats_summary, indent=2, default=str)}

CRITICAL: How to answer different queries:
1. "How many active products?" → Use product_status_distribution.active (NOT products_in_stock!)
2. "How many products in stock?" → Use products.products_in_stock
3. "Total products?" → Use products.total_products

REMEMBER:
- Active products = products with status="active" (use product_status_distribution.active)
- Products in stock = products with inventory > 0 (use products_in_stock)
- These are DIFFERENT things!

Return ONLY JSON:
{{
    "answer": "your natural language answer",
    "intent": "the type of query",
    "confidence": 0.8
}}"""

            if model_manager.auto_load_best_model(query):
                result = model_manager.inference(stats_prompt, max_tokens=200, temperature=0.5)
                response_text = result.get("text", "")
                parsed = safe_parse_llm_json(response_text)

                if parsed and parsed.get("answer"):
                    # Double-check for active products queries
                    if "active" in query_lower and "product" in query_lower:
                        # If LLM says 0 but we have active products, override
                        if "product_status_distribution" in stats_summary:
                            active_count = stats_summary["product_status_distribution"].get("active", 0)
                            if active_count > 0 and ("0" in parsed["answer"] or "don't have any" in parsed["answer"].lower()):
                                logger.warning(f"LLM said 0 active products but we have {active_count}, overriding")
                                # Fall through to pattern matching
                            else:
                                return {
                                    "answer": parsed["answer"],
                                    "intent": parsed.get("intent", "general"),
                                    "confidence": parsed.get("confidence", 0.8),
                                    "structured_data": None
                                }
                    else:
                        return {
                            "answer": parsed["answer"],
                            "intent": parsed.get("intent", "general"),
                            "confidence": parsed.get("confidence", 0.8),
                            "structured_data": None
                        }
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}, using pattern matching")

        # If LLM fails, use pattern matching as last resort
        answer = ""
        intent = "general"

        # Handle "active products" query
        if "active" in query_lower and "product" in query_lower:
            # Use prepared_data which has product_status_distribution
            for domain, data in prepared_data.items():
                if domain == "products":
                    # First try to get from product_status_distribution if available
                    if "product_status_distribution" in data:
                        active_count = data["product_status_distribution"].get("active", 0)
                        if active_count == 0:
                            answer = "You have 0 active products."
                        elif active_count == 1:
                            answer = "You have 1 active product."
                        else:
                            answer = f"You have {active_count} active products."
                        intent = "product_inquiry"
                        break
            # If not found in prepared_data, try raw data
            if not answer:
                for domain, data in all_data.items():
                    if domain == "products" and "products" in data:
                        products_list = data.get("products", [])
                        # Count active products (status = 'active' or status = '1' or status = 1)
                        active_count = 0
                        for product in products_list:
                            status = str(product.get("status", "")).lower()
                            if status in ["active", "1", "true"]:
                                active_count += 1

                        if active_count == 0:
                            answer = "You have 0 active products."
                        elif active_count == 1:
                            answer = "You have 1 active product."
                        else:
                            answer = f"You have {active_count} active products."
                        intent = "product_inquiry"
                        break

        # Handle general product count
        elif "how many" in query_lower and "product" in query_lower:
            for domain, data in all_data.items():
                if domain == "products" and "statistics" in data:
                    count = data["statistics"].get("total_products", 0)
                    answer = f"There are {count} total products in the store."
                    intent = "product_inquiry"
                    break

        # Handle orders queries
        elif "order" in query_lower:
            for domain, data in all_data.items():
                if domain == "sales" and "statistics" in data:
                    stats = data["statistics"]
                    total_orders = stats.get("total_orders", 0)
                    date_range = stats.get("date_range", {})

                    if "today" in query_lower:
                        if total_orders == 0:
                            answer = "You don't have any orders today."
                        elif total_orders == 1:
                            answer = "You have 1 order today."
                        else:
                            answer = f"You have {total_orders} orders today."
                    elif "yesterday" in query_lower:
                        if total_orders == 0:
                            answer = "You didn't have any orders yesterday."
                        else:
                            answer = f"You had {total_orders} orders yesterday."
                    else:
                        if total_orders == 0:
                            answer = "No orders found for the specified period."
                        else:
                            answer = f"You have {total_orders} orders."

                    intent = "order_inquiry"
                    break

        # Handle sales/revenue queries
        elif "sales" in query_lower or "revenue" in query_lower:
            for domain, data in all_data.items():
                if domain == "sales" and "statistics" in data:
                    stats = data["statistics"]
                    total_revenue = stats.get("total_revenue", 0)
                    total_orders = stats.get("total_orders", 0)

                    # Check if this is about a specific time period
                    if "this week" in query_lower or "week" in query_lower:
                        # Look at daily sales for the last 7 days
                        if "daily_sales" in data:
                            week_revenue = sum(day.get("revenue", 0) for day in data["daily_sales"][:7])
                            week_orders = sum(day.get("orders", 0) for day in data["daily_sales"][:7])
                            answer = f"Total sales this week: ${week_revenue:.2f} from {week_orders} orders"
                        else:
                            answer = f"Total revenue: ${total_revenue:.2f}, Orders: {total_orders}"
                    else:
                        answer = f"Total revenue: ${total_revenue:.2f}, Orders: {total_orders}"

                    intent = "sales_inquiry"
                    break

        # Try to extract relevant information based on keywords
        elif "price" in query_lower:
            for domain, data in all_data.items():
                if domain == "products" and "skus" in data:
                    prices = [sku.get("price", 0) for sku in data["skus"] if sku.get("price")]
                    if prices:
                        answer = f"Price range: ${min(prices)} - ${max(prices)}, Average: ${sum(prices)/len(prices):.2f}"
                        break

        elif "product" in query_lower and "count" in query_lower:
            for domain, data in all_data.items():
                if domain == "products" and "statistics" in data:
                    count = data["statistics"].get("total_products", 0)
                    if count == 0:
                        answer = "You don't have any products in your store."
                    elif count == 1:
                        answer = "You have 1 product in your store."
                    else:
                        answer = f"You have {count} products in your store."
                    intent = "product_inquiry"
                    break

        elif "sales" in query_lower or "revenue" in query_lower:
            for domain, data in all_data.items():
                if domain == "sales" and "statistics" in data:
                    stats = data["statistics"]
                    total_revenue = stats.get('total_revenue', 0)
                    total_orders = stats.get('total_orders', 0)

                    if total_revenue == 0:
                        answer = "You don't have any sales revenue yet."
                    else:
                        answer = f"Your total revenue is ${total_revenue:,.2f} from {total_orders} orders."
                    intent = "sales_inquiry"
                    break

        # If no specific match found, provide a helpful response
        if not answer:
            # Try to provide some general statistics if available
            for domain, data in all_data.items():
                if domain == "sales" and "statistics" in data:
                    stats = data["statistics"]
                    total_orders = stats.get("total_orders", 0)

                    if total_orders == 0:
                        answer = "I couldn't find any specific data for your query. You don't have any orders or sales data yet."
                    else:
                        answer = f"I found {total_orders} orders in your data. Please be more specific about what you'd like to know."
                    break

            # Final fallback
            if not answer:
                answer = "I couldn't find specific information for your query. Please try rephrasing or be more specific about what you'd like to know."

        return {
            "answer": answer,
            "intent": intent,
            "confidence": 0.5,
            "structured_data": None
        }


# Global instance
universal_llm_processor = UniversalLLMProcessor()