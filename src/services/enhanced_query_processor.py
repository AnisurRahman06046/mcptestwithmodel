"""
Enhanced Query Processor with Classification and Deterministic Processing
Integrates with existing universal processor
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.services.query_classifier import QueryClassifier, ClassificationResult
from src.services.deterministic_processor import DeterministicProcessor
from src.services.universal_llm_processor import UniversalLLMProcessor
from src.database.mongodb import mongodb_client

logger = logging.getLogger(__name__)


class EnhancedQueryProcessor:
    """
    Enhanced query processor that combines:
    1. Query classification with disambiguation
    2. Deterministic processing for factual queries
    3. LLM processing for complex queries
    """

    def __init__(self):
        """Initialize all components"""
        self.classifier = QueryClassifier()
        self.deterministic = DeterministicProcessor(mongodb_client=mongodb_client)
        self.llm_processor = UniversalLLMProcessor()

        # Track metrics
        self.metrics = {
            "total_queries": 0,
            "deterministic_handled": 0,
            "llm_handled": 0,
            "disambiguations": 0,
            "errors": 0
        }

    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for query processing

        Args:
            query: User query
            context: Context including shop_id, user_id, etc.

        Returns:
            Response dictionary with answer and metadata
        """
        start_time = datetime.utcnow()
        self.metrics["total_queries"] += 1

        try:
            # Step 1: Classify the query
            classification = self.classifier.classify(query, context)
            logger.info(f"Query classified as '{classification.intent}' with confidence {classification.confidence:.2f}")

            # Step 2: Handle disambiguation if needed
            if classification.needs_clarification:
                self.metrics["disambiguations"] += 1
                return self._create_disambiguation_response(classification, query)

            # Step 3: Check if query is unknown
            if classification.intent == "unknown":
                logger.warning(f"Unknown query, falling back to LLM: {query[:50]}")
                return await self._process_with_llm(query, context, classification)

            # Step 4: Process deterministically if applicable
            if classification.use_deterministic:
                logger.info(f"Processing deterministically: {classification.intent}")
                result = await self.deterministic.process(classification.intent, context)

                if result["success"]:
                    self.metrics["deterministic_handled"] += 1
                    return self._format_deterministic_response(result, classification, start_time)
                else:
                    logger.warning(f"Deterministic processing failed, falling back to LLM")

            # Step 5: Process with LLM for complex queries
            return await self._process_with_llm(query, context, classification)

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Query processing error: {e}", exc_info=True)
            return self._create_error_response(str(e))

    async def handle_disambiguation_response(self,
                                            original_query: str,
                                            selected_intent: str,
                                            context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user's response to disambiguation

        Args:
            original_query: The original ambiguous query
            selected_intent: The intent selected by user
            context: Query context

        Returns:
            Processed response
        """
        logger.info(f"User selected intent: {selected_intent} for query: {original_query[:50]}")

        # Get intent configuration
        intent_config = self.classifier.intent_configs.get(selected_intent)

        if not intent_config:
            return self._create_error_response(f"Invalid intent selected: {selected_intent}")

        # Create a classification result for the selected intent
        classification = ClassificationResult(
            intent=selected_intent,
            confidence=1.0,  # User explicitly selected
            method="user_selection",
            use_deterministic=intent_config.get("use_deterministic", False),
            data_preparation=intent_config.get("data_preparation", "full"),
            token_limit=intent_config.get("token_limit", 15000)
        )

        # Process based on intent type
        if classification.use_deterministic:
            result = await self.deterministic.process(selected_intent, context)
            if result["success"]:
                return self._format_deterministic_response(
                    result,
                    classification,
                    datetime.utcnow()
                )

        # Fall back to LLM
        return await self._process_with_llm(original_query, context, classification)

    async def _process_with_llm(self,
                                query: str,
                                context: Dict[str, Any],
                                classification: ClassificationResult) -> Dict[str, Any]:
        """Process query with LLM"""
        self.metrics["llm_handled"] += 1

        # Use the classification metadata to optimize LLM processing
        # The LLM processor can use data_preparation hint to minimize tokens
        enhanced_context = {
            **context,
            "classification": {
                "intent": classification.intent,
                "confidence": classification.confidence,
                "data_preparation": classification.data_preparation,
                "token_limit": classification.token_limit
            }
        }

        # Call the existing universal LLM processor
        result = await self.llm_processor.process_query(query, enhanced_context)

        # Add classification metadata to result
        if result.get("success"):
            result["classification"] = classification.to_dict()

        return result

    def _create_disambiguation_response(self,
                                       classification: ClassificationResult,
                                       query: str) -> Dict[str, Any]:
        """Create response for disambiguation"""
        return {
            "success": True,
            "needs_clarification": True,
            "original_query": query,
            "question": classification.metadata.get("question", "Please clarify your query:"),
            "options": classification.disambiguation_options,
            "metadata": {
                "confidence": classification.confidence,
                "method": classification.method,
                "trigger_words": classification.metadata.get("trigger_words", [])
            }
        }

    def _format_deterministic_response(self,
                                      result: Dict[str, Any],
                                      classification: ClassificationResult,
                                      start_time: datetime) -> Dict[str, Any]:
        """Format deterministic processor response"""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "response": result["response"],
            "structured_data": result.get("data"),
            "metadata": {
                "method": "deterministic",
                "intent": classification.intent,
                "confidence": classification.confidence,
                "classification_method": classification.method,
                "execution_time_ms": int(execution_time),
                "cached": result.get("metadata", {}).get("cached", False)
            }
        }

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "success": False,
            "error": error_message,
            "response": "I encountered an error processing your query. Please try again.",
            "metadata": {
                "method": "error"
            }
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics"""
        total = self.metrics["total_queries"] or 1

        return {
            **self.metrics,
            "deterministic_rate": self.metrics["deterministic_handled"] / total,
            "llm_rate": self.metrics["llm_handled"] / total,
            "disambiguation_rate": self.metrics["disambiguations"] / total,
            "error_rate": self.metrics["errors"] / total,
            "classifier_metrics": self.classifier.get_metrics(),
            "deterministic_metrics": self.deterministic.get_metrics()
        }


# Singleton instance
enhanced_query_processor = EnhancedQueryProcessor()