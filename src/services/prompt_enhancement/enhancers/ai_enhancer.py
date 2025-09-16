"""
AI-driven prompt enhancer using intelligent prompt engineering.
"""

import time
import logging
from typing import Optional, Dict, Any

from ..interfaces import IPromptEnhancer, IModelManager, IQueryAnalyzer
from ..models import (
    EnhancementRequest,
    EnhancementResult,
    EnhancementMethod,
    QueryComplexity,
    EnhancementLevel
)

logger = logging.getLogger(__name__)


class AIPromptEnhancer(IPromptEnhancer):
    """
    AI-driven prompt enhancer using dynamic prompt engineering.
    Adapts enhancement strategy based on query analysis.
    """

    def __init__(self, model_manager: IModelManager, query_analyzer: IQueryAnalyzer):
        """
        Initialize AI enhancer.

        Args:
            model_manager: Model manager for AI inference
            query_analyzer: Query analyzer for context
        """
        self.model_manager = model_manager
        self.query_analyzer = query_analyzer
        self.name = "ai_dynamic_enhancer"

        # Enhancement templates by level
        self._enhancement_instructions = {
            EnhancementLevel.MINIMAL: {
                "instruction": """Add essential business context and key metrics:
- Include primary KPIs (revenue, units, performance)
- Add time period clarity
- Specify data breakdown needs""",
                "max_tokens": 80,  # Increased for complete sentences
                "temperature": 0.2
            },
            EnhancementLevel.STANDARD: {
                "instruction": """Transform to be comprehensive and actionable:
- Add detailed business metrics (revenue, units sold, average order value, profit margins)
- Specify breakdown requirements (by product, category, time period)
- Include performance indicators and trend analysis
- Add comparative context (growth rates, period comparisons)
- Make it optimal for business intelligence tools""",
                "max_tokens": 100,  # Increased for complete sentences
                "temperature": 0.3
            },
            EnhancementLevel.COMPREHENSIVE: {
                "instruction": """Create a detailed, enterprise-level business intelligence query:
- Include comprehensive KPIs (revenue, profit, units sold, conversion rates, customer metrics)
- Specify detailed breakdowns (by product, category, customer segment, geography)
- Add analytical requirements (trends, comparisons, growth rates, forecasting)
- Include performance benchmarks and target comparisons
- Request actionable insights and recommendations
- Ensure optimal structure for advanced business analytics""",
                "max_tokens": 150,  # Increased significantly for full comprehensive enhancements
                "temperature": 0.4
            }
        }

    async def enhance(self, request: EnhancementRequest) -> EnhancementResult:
        """
        Enhance query using AI with intelligent prompt engineering.

        Args:
            request: Enhancement request with query and context

        Returns:
            EnhancementResult: Enhanced query with metadata
        """
        start_time = time.time()

        try:
            # Analyze query to determine enhancement strategy
            analysis = await self.query_analyzer.analyze(request.query, request.context)

            # Get enhancement level from analysis
            enhancement_level = analysis.recommended_enhancement_level

            # Override with user preference if provided
            if request.context and request.context.preferred_enhancement_level:
                enhancement_level = request.context.preferred_enhancement_level

            # Create enhancement prompt
            enhancement_prompt = self._create_enhancement_prompt(
                request.query,
                enhancement_level,
                analysis,
                request.context
            )

            # Get enhancement configuration
            config = self._enhancement_instructions[enhancement_level]

            # Perform AI enhancement
            model_result = await self.model_manager.inference(
                prompt=enhancement_prompt,
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )

            # Process and validate result
            raw_output = model_result.get("text", "")
            logger.info(f"Raw AI output for '{request.query}': {repr(raw_output)}")

            enhanced_query = self._process_enhancement_result(
                raw_output,
                request.query
            )

            logger.info(f"Processed enhancement: '{request.query}' -> '{enhanced_query}'")

            # Calculate confidence
            confidence = self._calculate_confidence(
                request.query,
                enhanced_query,
                analysis,
                model_result
            )

            processing_time = (time.time() - start_time) * 1000

            return EnhancementResult(
                original_query=request.query,
                enhanced_query=enhanced_query,
                method=EnhancementMethod.AI_DYNAMIC,
                confidence=confidence,
                processing_time_ms=processing_time,
                analysis=analysis,
                context=request.context,
                metadata={
                    "enhancement_level": enhancement_level.value,
                    "model_tokens_used": model_result.get("token_usage", {}).get("total_tokens", 0),
                    "model_processing_time": model_result.get("processing_time", 0)
                }
            )

        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            processing_time = (time.time() - start_time) * 1000

            return EnhancementResult(
                original_query=request.query,
                enhanced_query=request.query,  # Fallback to original
                method=EnhancementMethod.FALLBACK,
                confidence=0.0,
                processing_time_ms=processing_time,
                context=request.context,
                metadata={"error": str(e)}
            )

    def _create_enhancement_prompt(
        self,
        query: str,
        level: EnhancementLevel,
        analysis: Any,
        context: Optional[Any] = None
    ) -> str:
        """
        Create contextually appropriate enhancement prompt.

        Args:
            query: Original user query
            level: Enhancement level to apply
            analysis: Query analysis result
            context: Optional context information

        Returns:
            str: Formatted enhancement prompt
        """
        # Get base instruction for this level
        instruction = self._enhancement_instructions[level]["instruction"]

        # Add intent context if available
        intent_context = ""
        if analysis.estimated_intent:
            intent_map = {
                'inventory_inquiry': 'product and inventory management',
                'sales_inquiry': 'sales performance and revenue analysis',
                'customer_inquiry': 'customer analytics and insights',
                'order_inquiry': 'order processing and fulfillment',
                'analytics_inquiry': 'business intelligence and analytics'
            }
            domain = intent_map.get(analysis.estimated_intent, 'business data analysis')
            intent_context = f"\nDomain Focus: {domain}"

        # Add complexity context
        complexity_guidance = {
            QueryComplexity.SIMPLE: "The query is very brief. Expand significantly with business context.",
            QueryComplexity.MODERATE: "Add business terminology and specify data requirements.",
            QueryComplexity.STRUCTURED: "Enhance clarity and add performance metrics context.",
            QueryComplexity.COMPLEX: "Make minor improvements for better data retrieval."
        }

        complexity_note = complexity_guidance.get(analysis.complexity, "")

        # Construct final prompt
        prompt = f"""Transform this e-commerce query into a comprehensive business intelligence request.

Original query: "{query}"

Enhancement Requirements:
{instruction}

Examples of rich enhancements:
- "sales" → "provide comprehensive sales analytics including total revenue, units sold, average order value, profit margins, conversion rates, and month-over-month growth trends"
- "customers" → "show detailed customer analytics including demographics, purchase behavior, lifetime value, retention rates, and segmentation insights"
- "inventory" → "display complete inventory analysis including stock levels, turnover rates, low stock alerts, reorder recommendations, and demand forecasting"

Create a detailed, professional business query that:
- Uses comprehensive business terminology and KPIs
- Specifies multiple relevant metrics and breakdowns
- Includes analytical requirements (trends, comparisons, insights)
- Is optimized for advanced business intelligence tools
- Maintains the original intent but significantly expands scope

Enhanced business query:"""

        return prompt

    def _process_enhancement_result(self, raw_result: str, original_query: str) -> str:
        """
        Process and clean AI enhancement result.
        """
        if not raw_result:
            return original_query

        logger.debug(f"Processing raw result: {repr(raw_result)}")

        # Step 1: Basic cleanup
        enhanced = raw_result.strip()

        # Step 2: Extract content from quotes if present
        # Look for quoted content: "actual enhanced query"
        import re
        quoted_match = re.search(r'[""\'](.*?)[""\'.]', enhanced)
        if quoted_match:
            extracted = quoted_match.group(1).strip()
            if len(extracted) > len(original_query):  # Only use if it's actually enhanced
                enhanced = extracted
                logger.debug(f"Extracted quoted content: {repr(enhanced)}")

        # Step 3: Handle rich AI responses with arrows and examples
        # Extract from arrow pattern: "query" → "enhanced query"
        import re
        arrow_pattern = r'"[^"]*"\s*→\s*"([^"]*)"'
        arrow_match = re.search(arrow_pattern, enhanced)
        if arrow_match:
            extracted = arrow_match.group(1).strip()
            if len(extracted) > len(original_query):
                enhanced = extracted
                logger.debug(f"Extracted from arrow pattern: {repr(enhanced)}")

        # Remove explanations that come after the enhanced query
        explanation_markers = [
            '\n\nThis query',
            '\n\nThe enhanced',
            '. This aims',
            '. The query',
            '\n\nExplanation'
        ]

        for marker in explanation_markers:
            if marker in enhanced:
                enhanced = enhanced.split(marker)[0].strip()
                logger.debug(f"Removed explanation after '{marker}': {repr(enhanced)}")
                break

        # Step 4: Final cleanup
        enhanced = enhanced.strip().rstrip('."\'""''').strip()

        logger.debug(f"Final processed: {repr(enhanced)}")

        # Step 5: Validation
        if (not enhanced or
            len(enhanced) < 3 or
            enhanced.lower() == original_query.lower() or
            enhanced.endswith('?')):
            logger.debug("Enhancement validation failed, returning original")
            return original_query

        return enhanced

    def _calculate_confidence(
        self,
        original: str,
        enhanced: str,
        analysis: Any,
        model_result: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence in enhancement quality.

        Args:
            original: Original query
            enhanced: Enhanced query
            analysis: Query analysis
            model_result: Model inference result

        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if enhanced == original:
            return 0.0

        base_confidence = 0.8  # Higher base confidence for AI enhancement

        # Length ratio check (good enhancement should be reasonable)
        length_ratio = len(enhanced) / len(original) if original else 1
        if 1.2 <= length_ratio <= 3.0:
            base_confidence += 0.1
        elif length_ratio > 3.0:
            base_confidence -= 0.2

        # Business terms addition check
        business_terms = {
            'sales', 'revenue', 'data', 'analysis', 'performance',
            'metrics', 'insights', 'analytics', 'report'
        }

        original_terms = sum(1 for term in business_terms if term in original.lower())
        enhanced_terms = sum(1 for term in business_terms if term in enhanced.lower())

        if enhanced_terms > original_terms:
            base_confidence += 0.1

        # Query complexity adjustment
        if analysis.complexity == QueryComplexity.SIMPLE:
            base_confidence += 0.1  # Simple queries benefit most from enhancement
        elif analysis.complexity == QueryComplexity.COMPLEX:
            base_confidence -= 0.1  # Complex queries need less enhancement

        # Model confidence (if available)
        if "confidence" in model_result:
            model_confidence = model_result["confidence"]
            base_confidence = (base_confidence + model_confidence) / 2

        return max(0.0, min(1.0, base_confidence))

    def is_available(self) -> bool:
        """Check if AI enhancer is available"""
        return self.model_manager.is_available()

    def get_name(self) -> str:
        """Get enhancer name"""
        return self.name