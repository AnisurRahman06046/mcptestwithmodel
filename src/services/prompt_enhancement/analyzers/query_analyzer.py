"""
Intelligent query analyzer for determining enhancement strategy.
"""

import re
import logging
from typing import Optional, Set, Dict, Any

from ..interfaces import IQueryAnalyzer, IIntentPredictor
from ..models import QueryAnalysis, QueryComplexity, EnhancementContext

logger = logging.getLogger(__name__)


class IntelligentQueryAnalyzer(IQueryAnalyzer):
    """
    Analyzes user queries to determine complexity and enhancement needs.
    Uses linguistic patterns and business domain knowledge.
    """

    def __init__(self, intent_predictor: Optional[IIntentPredictor] = None):
        """
        Initialize analyzer.

        Args:
            intent_predictor: Optional intent predictor for context
        """
        self.intent_predictor = intent_predictor

        # Business domain terms for e-commerce
        self._business_terms: Set[str] = {
            'sales', 'revenue', 'profit', 'earnings', 'income',
            'products', 'items', 'inventory', 'stock', 'catalog',
            'customers', 'clients', 'buyers', 'users', 'shoppers',
            'orders', 'purchases', 'transactions', 'cart', 'checkout',
            'analytics', 'metrics', 'performance', 'trends', 'insights',
            'data', 'report', 'analysis', 'statistics', 'dashboard'
        }

        # Time reference patterns
        self._time_patterns: Set[str] = {
            'today', 'yesterday', 'tomorrow', 'now', 'current',
            'last', 'this', 'next', 'past', 'recent', 'latest',
            'week', 'month', 'year', 'quarter', 'day', 'daily',
            'weekly', 'monthly', 'yearly', 'quarterly'
        }

        # Action words that indicate specific requests
        self._action_words: Set[str] = {
            'show', 'display', 'get', 'fetch', 'retrieve', 'find',
            'list', 'provide', 'give', 'tell', 'explain', 'analyze',
            'compare', 'calculate', 'summarize', 'report', 'update'
        }

    async def analyze(self, query: str, context: Optional[EnhancementContext] = None) -> QueryAnalysis:
        """
        Analyze query for complexity and characteristics.

        Args:
            query: User query to analyze
            context: Optional enhancement context

        Returns:
            QueryAnalysis: Comprehensive analysis result
        """
        try:
            # Basic text analysis
            word_count = len(query.split())
            query_lower = query.lower().strip()

            # Check for business terms
            has_business_terms = self._contains_business_terms(query_lower)

            # Check for time references
            has_time_references = self._contains_time_references(query_lower)

            # Determine complexity
            complexity = self._determine_complexity(
                query_lower, word_count, has_business_terms, has_time_references
            )

            # Predict intent if predictor available
            estimated_intent = None
            intent_confidence = 0.0
            if self.intent_predictor:
                try:
                    estimated_intent = await self.intent_predictor.predict_intent(query, context)
                    intent_confidence = 0.8 if estimated_intent else 0.0
                except Exception as e:
                    logger.warning(f"Intent prediction failed: {e}")

            return QueryAnalysis(
                complexity=complexity,
                word_count=word_count,
                has_time_references=has_time_references,
                has_business_terms=has_business_terms,
                estimated_intent=estimated_intent,
                confidence=intent_confidence
            )

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Return safe default analysis
            return QueryAnalysis(
                complexity=QueryComplexity.MODERATE,
                word_count=len(query.split()),
                has_time_references=False,
                has_business_terms=False,
                estimated_intent=None,
                confidence=0.0
            )

    def _contains_business_terms(self, query_lower: str) -> bool:
        """Check if query contains business-related terms"""
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        return bool(query_words.intersection(self._business_terms))

    def _contains_time_references(self, query_lower: str) -> bool:
        """Check if query contains time-related terms"""
        query_words = set(re.findall(r'\b\w+\b', query_lower))

        # Check for explicit time words
        if query_words.intersection(self._time_patterns):
            return True

        # Check for time patterns like "last 30 days"
        time_patterns = [
            r'\blast\s+\d+\s+(days?|weeks?|months?|years?)\b',
            r'\bpast\s+\d+\s+(days?|weeks?|months?|years?)\b',
            r'\bthis\s+(week|month|year|quarter)\b',
            r'\blast\s+(week|month|year|quarter)\b'
        ]

        for pattern in time_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def _determine_complexity(
        self,
        query_lower: str,
        word_count: int,
        has_business_terms: bool,
        has_time_references: bool
    ) -> QueryComplexity:
        """
        Determine query complexity based on multiple factors.

        Args:
            query_lower: Lowercase query
            word_count: Number of words
            has_business_terms: Whether query has business terms
            has_time_references: Whether query has time references

        Returns:
            QueryComplexity: Determined complexity level
        """
        # Single word queries are always simple
        if word_count <= 1:
            return QueryComplexity.SIMPLE

        # Very short queries without context
        if word_count <= 2 and not has_business_terms:
            return QueryComplexity.SIMPLE

        # Check for action words indicating structure
        has_action_words = any(word in query_lower for word in self._action_words)

        # Check for question patterns
        is_question = query_lower.startswith(('what', 'how', 'when', 'where', 'why', 'which', 'who'))

        # Structured queries have good indicators
        if (has_business_terms and has_time_references) or \
           (has_action_words and has_business_terms) or \
           (is_question and word_count >= 4):
            return QueryComplexity.STRUCTURED

        # Complex queries are well-formed and detailed
        if word_count >= 8 and (has_business_terms or has_time_references):
            return QueryComplexity.COMPLEX

        # Complex queries with multiple clauses
        if any(connector in query_lower for connector in ['and', 'or', 'but', 'with', 'including']):
            return QueryComplexity.COMPLEX

        # Moderate complexity for everything else
        return QueryComplexity.MODERATE


class FastIntentPredictor(IIntentPredictor):
    """
    Fast rule-based intent predictor for query analysis.
    Used as a lightweight alternative to full AI intent classification.
    """

    def __init__(self):
        """Initialize with intent patterns"""
        self._intent_patterns = {
            'inventory_inquiry': [
                r'\b(products?|items?|inventory|stock|catalog)\b',
                r'\b(show|list|display).*products?\b',
                r'\bavailable\s+(products?|items?)\b'
            ],
            'sales_inquiry': [
                r'\b(sales?|revenue|earnings?|income)\b',
                r'\btotal.*sales?\b',
                r'\bsales?\s+(data|report|analysis)\b'
            ],
            'customer_inquiry': [
                r'\b(customers?|clients?|buyers?|users?)\b',
                r'\btop.*customers?\b',
                r'\bcustomer.*(data|info|analytics)\b'
            ],
            'order_inquiry': [
                r'\b(orders?|purchases?|transactions?)\b',
                r'\border.*(status|details|history)\b',
                r'\brecent.*orders?\b'
            ],
            'analytics_inquiry': [
                r'\b(analyz|trends?|insights?|metrics?|performance)\b',
                r'\bcompare.*with\b',
                r'\b(dashboard|report|statistics)\b'
            ]
        }

    async def predict_intent(self, query: str, context: Optional[EnhancementContext] = None) -> Optional[str]:
        """
        Predict intent using pattern matching.

        Args:
            query: User query
            context: Optional context (unused in this implementation)

        Returns:
            Optional[str]: Predicted intent or None
        """
        query_lower = query.lower()

        # Score each intent
        intent_scores = {}
        for intent, patterns in self._intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > 0:
                intent_scores[intent] = score

        # Return highest scoring intent
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)

        return None

    def get_supported_intents(self) -> list[str]:
        """Get list of supported intents"""
        return list(self._intent_patterns.keys())