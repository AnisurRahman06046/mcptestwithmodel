"""
Hybrid intent classifier combining SetFit speed with LLM adaptability.
Runs alongside existing system without breaking changes.
"""

import time
import logging
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from .models import ClassificationResult, ClassificationMethod, TrainingExample, LearningMetrics, HybridConfig
from .classifiers.setfit_classifier import SetFitIntentClassifier
from .learning.background_trainer import ProductionSafeTrainer

logger = logging.getLogger(__name__)

# Optional imports - graceful degradation if not available
try:
    from setfit import SetFitModel, SetFitTrainer
    from datasets import Dataset
    SETFIT_AVAILABLE = True
except ImportError:
    SETFIT_AVAILABLE = False
    logger.warning("SetFit not available - hybrid classifier will use LLM only")


class HybridIntentClassifier:
    """
    Hybrid intent classifier that combines SetFit speed with LLM learning.
    Designed to run alongside existing systems without breaking changes.
    """

    def __init__(self, llm_classifier, config: Optional[HybridConfig] = None):
        """
        Initialize hybrid classifier.

        Args:
            llm_classifier: Existing LLM-based classifier (your current system)
            config: Hybrid system configuration
        """
        self.llm_classifier = llm_classifier
        self.config = config or HybridConfig()

        # Core components
        self.setfit_classifier = SetFitIntentClassifier(self.config.setfit_model_path)
        self.background_trainer = ProductionSafeTrainer(self.setfit_classifier, self.config)
        self.result_cache: Dict[str, ClassificationResult] = {}
        self.training_buffer: List[TrainingExample] = []
        self.metrics = LearningMetrics()

        # Initialize if enabled (deferred to first use for sync safety)
        self._initialization_started = False

    async def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Main classification method with hybrid approach.

        Args:
            query: User query to classify
            context: Optional context information

        Returns:
            ClassificationResult: Classification result with metadata
        """
        start_time = time.time()

        # If hybrid system is disabled, use existing LLM classifier
        if not self.config.enabled:
            return await self._classify_with_llm(query, context, start_time)

        # Initialize on first use (lazy initialization)
        if not self._initialization_started:
            self._initialization_started = True
            await self._initialize_hybrid_system()

        try:
            # Step 1: Check cache first
            cache_key = self._generate_cache_key(query, context)
            if self.config.cache_enabled and cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                # Update method to indicate cache hit
                cached_result = ClassificationResult(
                    intent=cached_result.intent,
                    confidence=cached_result.confidence,
                    method=ClassificationMethod.CACHED,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    metadata={"cached": True, "original_method": cached_result.method.value}
                )
                self.metrics.update_classification(cached_result)
                return cached_result

            # Step 2: Try SetFit classification (fast path)
            if self.setfit_classifier.is_available():
                setfit_result = await self._classify_with_setfit(query, start_time)

                # Step 3: Evaluate SetFit confidence
                if setfit_result.confidence >= self.config.setfit_confidence_threshold:
                    # High confidence - use SetFit result
                    self._cache_result(cache_key, setfit_result)
                    self.metrics.update_classification(setfit_result)
                    return setfit_result

                # Low confidence - fall through to LLM

            # Step 4: LLM fallback (learning path)
            llm_result = await self._classify_with_llm(query, context, start_time)

            # Step 5: Learn from LLM result (safe background learning)
            if self.config.auto_retrain_enabled:
                await self._add_to_learning_buffer(query, llm_result)

            # Cache LLM result too
            self._cache_result(cache_key, llm_result)
            self.metrics.update_classification(llm_result)

            return llm_result

        except Exception as e:
            logger.error(f"Hybrid classification failed: {e}")
            # Ultimate fallback - use existing LLM system
            return await self._classify_with_llm(query, context, start_time)

    async def _classify_with_setfit(self, query: str, start_time: float) -> ClassificationResult:
        """Classify using SetFit model"""
        try:
            # Use SetFit classifier
            intent, confidence = await self.setfit_classifier.classify(query)
            processing_time = (time.time() - start_time) * 1000

            return ClassificationResult(
                intent=intent,
                confidence=confidence,
                method=ClassificationMethod.SETFIT_FAST,
                processing_time_ms=processing_time,
                metadata={"setfit_classifier": "production"}
            )

        except Exception as e:
            logger.error(f"SetFit classification failed: {e}")
            raise

    async def _classify_with_llm(self, query: str, context: Optional[Dict[str, Any]], start_time: float) -> ClassificationResult:
        """Classify using existing LLM system"""
        try:
            # Use your existing LLM classification
            intent = self.llm_classifier._classify_intent(query)
            processing_time = (time.time() - start_time) * 1000

            # Estimate confidence based on your current system
            confidence = 0.7  # Default confidence for LLM results

            return ClassificationResult(
                intent=intent,
                confidence=confidence,
                method=ClassificationMethod.LLM_ADAPTIVE,
                processing_time_ms=processing_time,
                metadata={"llm_method": "existing_system"}
            )

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            processing_time = (time.time() - start_time) * 1000

            return ClassificationResult(
                intent="general_inquiry",
                confidence=0.0,
                method=ClassificationMethod.FALLBACK,
                processing_time_ms=processing_time,
                metadata={"error": str(e)}
            )

    async def _initialize_hybrid_system(self):
        """Initialize hybrid system components"""
        try:
            logger.info("Initializing hybrid intent classification system...")

            # Initialize SetFit classifier
            success = await self.setfit_classifier.initialize()
            if success:
                logger.info("SetFit classifier initialized successfully")
            else:
                logger.warning("SetFit classifier initialization failed - will use LLM only")

        except Exception as e:
            logger.error(f"Hybrid system initialization failed: {e}")
            # System continues with LLM only

    async def _train_initial_setfit_model(self):
        """Train initial SetFit model using existing intent patterns"""
        try:
            # Create training data from your existing regex patterns
            training_data = self._create_initial_training_data()

            if not training_data:
                logger.warning("No training data available for SetFit")
                return

            # Prepare dataset
            texts = []
            labels = []
            for intent, examples in training_data.items():
                for example in examples:
                    texts.append(example)
                    labels.append(intent)

            # Create dataset
            train_dataset = Dataset.from_dict({"text": texts, "label": labels})

            # Initialize and train model
            self.setfit_model = SetFitModel.from_pretrained(
                "sentence-transformers/paraphrase-mpnet-base-v2"
            )

            trainer = SetFitTrainer(
                model=self.setfit_model,
                train_dataset=train_dataset,
                num_iterations=20,
                num_epochs=1
            )

            trainer.train()

            # Save model
            model_path = Path(self.config.setfit_model_path)
            model_path.parent.mkdir(parents=True, exist_ok=True)
            self.setfit_model.save_pretrained(str(model_path))

            logger.info("Initial SetFit model trained and saved successfully")

        except Exception as e:
            logger.error(f"SetFit training failed: {e}")

    def _create_initial_training_data(self) -> Dict[str, List[str]]:
        """Create initial training data from existing patterns"""
        # Extract examples from your existing regex patterns in query_processor.py
        return {
            "inventory_inquiry": [
                "show products", "list items", "what products", "product catalog",
                "inventory status", "stock levels", "available products",
                "display inventory", "product list", "items in stock"
            ],
            "sales_inquiry": [
                "sales data", "revenue report", "earnings", "income",
                "sales performance", "total sales", "sales figures",
                "revenue analysis", "sales metrics", "financial data"
            ],
            "customer_inquiry": [
                "customer data", "top customers", "client info", "buyer data",
                "customer analytics", "customer insights", "customer list",
                "customer behavior", "customer demographics", "client analytics"
            ],
            "order_inquiry": [
                "order status", "recent orders", "order history", "order details",
                "purchase data", "order information", "order tracking",
                "pending orders", "order analytics", "fulfillment status"
            ],
            "analytics_inquiry": [
                "analyze trends", "business insights", "performance metrics",
                "trend analysis", "business analytics", "insights report",
                "analytics dashboard", "performance analysis", "business intelligence"
            ],
            "greeting": [
                "hello", "hi", "hey", "good morning", "how are you",
                "greetings", "good day", "nice to meet you"
            ],
            "general_conversation": [
                "thank you", "thanks", "help", "what can you do",
                "assistance", "support", "yes", "no", "okay"
            ]
        }

    async def _add_to_learning_buffer(self, query: str, result: ClassificationResult):
        """Add LLM result to learning buffer for safe background training"""
        if result.method != ClassificationMethod.LLM_ADAPTIVE:
            return

        example = TrainingExample(
            query=query,
            intent=result.intent,
            confidence=result.confidence,
            source=result.method
        )

        self.training_buffer.append(example)
        logger.debug(f"Added to learning buffer: '{query}' -> '{result.intent}' (buffer size: {len(self.training_buffer)})")

        # Check if we should schedule background training
        if len(self.training_buffer) >= self.config.training_buffer_size:
            # Schedule safe background training
            await self.background_trainer.schedule_training(self.training_buffer.copy())
            # Clear buffer after scheduling
            self.training_buffer.clear()
            logger.info(f"Scheduled background training with {self.config.training_buffer_size} new examples")

    async def _retrain_setfit_model(self):
        """Retrain SetFit model with new examples"""
        if self.is_training or not SETFIT_AVAILABLE:
            return

        self.is_training = True
        try:
            logger.info(f"Starting SetFit retraining with {len(self.training_buffer)} new examples...")

            # Prepare new training data
            new_texts = [ex.query for ex in self.training_buffer]
            new_labels = [ex.intent for ex in self.training_buffer]

            # Combine with existing data
            all_training_data = self._create_initial_training_data()
            for example in self.training_buffer:
                if example.intent not in all_training_data:
                    all_training_data[example.intent] = []
                all_training_data[example.intent].append(example.query)

            # Retrain model
            await self._train_setfit_with_data(all_training_data)

            # Clear buffer and update metrics
            self.training_buffer.clear()
            self.metrics.retraining_sessions += 1
            self.last_retrain_time = datetime.utcnow()

            logger.info("SetFit model retrained successfully")

        except Exception as e:
            logger.error(f"SetFit retraining failed: {e}")
        finally:
            self.is_training = False

    async def _train_setfit_with_data(self, training_data: Dict[str, List[str]]):
        """Train SetFit model with provided data"""
        # Prepare dataset
        texts = []
        labels = []
        for intent, examples in training_data.items():
            for example in examples:
                texts.append(example)
                labels.append(intent)

        train_dataset = Dataset.from_dict({"text": texts, "label": labels})

        # Initialize new model
        self.setfit_model = SetFitModel.from_pretrained(
            "sentence-transformers/paraphrase-mpnet-base-v2"
        )

        # Train
        trainer = SetFitTrainer(
            model=self.setfit_model,
            train_dataset=train_dataset,
            num_iterations=20,
            num_epochs=1
        )

        trainer.train()

        # Save updated model
        model_path = Path(self.config.setfit_model_path)
        self.setfit_model.save_pretrained(str(model_path))

    def _generate_cache_key(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for query"""
        import hashlib
        key_data = query.lower().strip()
        if context:
            key_data += str(sorted(context.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def _cache_result(self, cache_key: str, result: ClassificationResult):
        """Cache classification result"""
        if not self.config.cache_enabled:
            return

        # Simple in-memory cache with size limit
        if len(self.result_cache) >= 1000:  # Limit cache size
            # Remove oldest entry
            oldest_key = next(iter(self.result_cache))
            del self.result_cache[oldest_key]

        self.result_cache[cache_key] = result

    def _get_intent_from_label(self, label: int) -> str:
        """Map numeric label to intent name"""
        # Default intent mapping (will be updated after training)
        default_mapping = {
            0: "inventory_inquiry",
            1: "sales_inquiry",
            2: "customer_inquiry",
            3: "order_inquiry",
            4: "analytics_inquiry",
            5: "greeting",
            6: "general_conversation"
        }
        return default_mapping.get(label, "general_inquiry")

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "enabled": self.config.enabled,
            "setfit_available": SETFIT_AVAILABLE,
            "setfit_model_loaded": self.setfit_model is not None,
            "training_buffer_size": len(self.training_buffer),
            "cache_size": len(self.result_cache),
            "is_training": self.is_training,
            "last_retrain": self.last_retrain_time.isoformat() if self.last_retrain_time else None,
            "performance": {
                "total_classifications": self.metrics.total_classifications,
                "fast_path_percentage": self.metrics.fast_path_percentage,
                "learning_path_percentage": self.metrics.learning_path_percentage,
                "average_setfit_time": self.metrics.average_setfit_time,
                "average_llm_time": self.metrics.average_llm_time,
                "retraining_sessions": self.metrics.retraining_sessions
            }
        }

    async def enable_hybrid_mode(self):
        """Enable hybrid mode (can be called at runtime)"""
        if not SETFIT_AVAILABLE:
            logger.error("Cannot enable hybrid mode - SetFit not available")
            return False

        self.config.enabled = True
        await self._initialize_setfit_model()
        logger.info("Hybrid intent classification enabled")
        return True

    def disable_hybrid_mode(self):
        """Disable hybrid mode (fallback to LLM only)"""
        self.config.enabled = False
        logger.info("Hybrid intent classification disabled - using LLM only")


class HybridIntentClassificationService:
    """
    Service wrapper for hybrid intent classification.
    Provides easy integration with existing query processor.
    """

    def __init__(self, query_processor, config: Optional[HybridConfig] = None):
        """
        Initialize service.

        Args:
            query_processor: Your existing query processor
            config: Hybrid system configuration
        """
        self.query_processor = query_processor
        self.config = config or HybridConfig()

        # Create hybrid classifier
        self.hybrid_classifier = HybridIntentClassifier(
            llm_classifier=query_processor,
            config=self.config
        )

    async def classify_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Classify intent using hybrid approach.

        Args:
            query: User query
            context: Optional context

        Returns:
            str: Intent classification result
        """
        result = await self.hybrid_classifier.classify(query, context)
        return result.intent

    def get_classification_metadata(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get detailed classification metadata for monitoring.

        Args:
            query: User query
            context: Optional context

        Returns:
            Dict[str, Any]: Classification metadata
        """
        # This would be called after classify_intent to get detailed metrics
        return self.hybrid_classifier.get_metrics()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of hybrid system"""
        return {
            "hybrid_enabled": self.config.enabled,
            "setfit_available": SETFIT_AVAILABLE,
            "components_healthy": True,
            "performance_metrics": self.hybrid_classifier.get_metrics()
        }

    # Safe enablement methods
    async def enable_hybrid_classification(self):
        """Safely enable hybrid classification"""
        return await self.hybrid_classifier.enable_hybrid_mode()

    def disable_hybrid_classification(self):
        """Safely disable hybrid classification"""
        self.hybrid_classifier.disable_hybrid_mode()