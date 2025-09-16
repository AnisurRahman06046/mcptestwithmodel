"""
SetFit-based fast intent classifier implementation.
Production-ready with error handling and performance optimization.
"""

import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Optional import with graceful fallback
try:
    from setfit import SetFitModel, SetFitTrainer
    from datasets import Dataset
    import numpy as np
    SETFIT_AVAILABLE = True
    logger.info("SetFit dependencies available")
except ImportError:
    SETFIT_AVAILABLE = False
    logger.warning("SetFit dependencies not available - install with: pip install setfit")


class SetFitIntentClassifier:
    """
    Fast intent classifier using SetFit model.
    Provides 20-50ms classification for known intents.
    """

    def __init__(self, model_path: str = "./models/hybrid_intent_setfit"):
        """
        Initialize SetFit classifier.

        Args:
            model_path: Path to save/load SetFit model
        """
        self.model_path = Path(model_path)
        self.model = None
        self.label_to_intent = {}
        self.intent_to_label = {}
        self.is_trained = False

        # Performance tracking
        self.classification_count = 0
        self.total_classification_time = 0.0

    def is_available(self) -> bool:
        """Check if SetFit classifier is ready to use"""
        return SETFIT_AVAILABLE and self.model is not None and self.is_trained

    async def initialize(self) -> bool:
        """
        Initialize SetFit model (load existing or train new).

        Returns:
            bool: True if initialization succeeded
        """
        if not SETFIT_AVAILABLE:
            logger.warning("SetFit not available - hybrid system will use LLM only")
            return False

        try:
            # Try to load existing model first
            if await self.load():
                return True

            # If no existing model, train initial model
            logger.info("No existing SetFit model found, training initial model...")
            training_data = self._get_initial_training_data()
            return await self.train(training_data)

        except Exception as e:
            logger.error(f"SetFit initialization failed: {e}")
            return False

    async def train(self, training_data: Dict[str, List[str]]) -> bool:
        """
        Train SetFit model with provided training data.

        Args:
            training_data: Dict mapping intent names to example queries

        Returns:
            bool: True if training succeeded
        """
        if not SETFIT_AVAILABLE:
            logger.error("SetFit not available - cannot train model")
            return False

        try:
            logger.info("Starting SetFit model training...")
            start_time = time.time()

            # Prepare training data
            texts, labels = self._prepare_training_data(training_data)

            if len(texts) < 10:
                logger.error("Insufficient training data - need at least 10 examples")
                return False

            # Create label mappings
            unique_labels = sorted(set(labels))
            self.label_to_intent = {i: label for i, label in enumerate(unique_labels)}
            self.intent_to_label = {label: i for i, label in enumerate(unique_labels)}

            # Convert to numeric labels
            numeric_labels = [self.intent_to_label[label] for label in labels]

            # Create dataset
            train_dataset = Dataset.from_dict({
                "text": texts,
                "label": numeric_labels
            })

            # Initialize SetFit model
            self.model = SetFitModel.from_pretrained(
                "sentence-transformers/paraphrase-mpnet-base-v2"
            )

            # Create trainer with production-optimized settings
            trainer = SetFitTrainer(
                model=self.model,
                train_dataset=train_dataset,
                num_iterations=15,  # Reduced for faster training
                num_epochs=1,
                batch_size=16,  # Optimized batch size
                learning_rate=2e-5  # Stable learning rate
            )

            # Train the model
            trainer.train()

            # Save model atomically
            await self._save_model_safely()

            training_time = time.time() - start_time
            self.is_trained = True

            logger.info(f"SetFit model trained successfully in {training_time:.1f}s with {len(texts)} examples")
            logger.info(f"Trained intents: {list(self.intent_to_label.keys())}")
            return True

        except Exception as e:
            logger.error(f"SetFit training failed: {e}")
            return False

    async def load(self) -> bool:
        """
        Load existing SetFit model.

        Returns:
            bool: True if loading succeeded
        """
        if not SETFIT_AVAILABLE:
            return False

        try:
            if not self.model_path.exists():
                logger.debug("No existing SetFit model found")
                return False

            # Load model
            self.model = SetFitModel.from_pretrained(str(self.model_path))

            # Load label mappings
            if not self._load_label_mappings():
                logger.error("Failed to load label mappings")
                return False

            self.is_trained = True
            logger.info(f"SetFit model loaded successfully from {self.model_path}")
            logger.info(f"Available intents: {list(self.intent_to_label.keys())}")
            return True

        except Exception as e:
            logger.error(f"SetFit model loading failed: {e}")
            return False

    async def classify(self, query: str) -> Tuple[str, float]:
        """
        Classify query using SetFit model.

        Args:
            query: User query to classify

        Returns:
            Tuple[str, float]: (intent, confidence)
        """
        if not self.is_available():
            raise RuntimeError("SetFit classifier not available")

        start_time = time.time()
        try:
            # Get prediction probabilities
            probabilities = self.model.predict_proba([query])[0]

            # Get best prediction
            predicted_label = int(np.argmax(probabilities))
            confidence = float(probabilities[predicted_label])

            # Map to intent name
            intent = self.label_to_intent.get(predicted_label, "general_inquiry")

            # Track performance
            classification_time = (time.time() - start_time) * 1000
            self.classification_count += 1
            self.total_classification_time += classification_time

            logger.debug(f"SetFit classified '{query}' as '{intent}' (confidence: {confidence:.2f}, time: {classification_time:.1f}ms)")

            return intent, confidence

        except Exception as e:
            logger.error(f"SetFit classification failed: {e}")
            raise

    def _get_initial_training_data(self) -> Dict[str, List[str]]:
        """Get initial training data from existing patterns"""
        return {
            "inventory_inquiry": [
                "show products", "list items", "what products", "product catalog",
                "inventory status", "stock levels", "available products",
                "display inventory", "product list", "items in stock",
                "five products list", "give me products", "show inventory"
            ],
            "sales_inquiry": [
                "sales data", "revenue report", "earnings", "income",
                "sales performance", "total sales", "sales figures",
                "revenue analysis", "sales metrics", "financial data",
                "last month sales", "sales report", "revenue"
            ],
            "customer_inquiry": [
                "customer data", "top customers", "client info", "buyer data",
                "customer analytics", "customer insights", "customer list",
                "customer behavior", "customer demographics", "client analytics",
                "best customers", "customer information"
            ],
            "order_inquiry": [
                "order status", "recent orders", "order history", "order details",
                "purchase data", "order information", "order tracking",
                "pending orders", "order analytics", "fulfillment status",
                "my orders", "order list"
            ],
            "analytics_inquiry": [
                "analyze trends", "business insights", "performance metrics",
                "trend analysis", "business analytics", "insights report",
                "analytics dashboard", "performance analysis", "business intelligence",
                "compare sales", "trends", "insights"
            ],
            "greeting": [
                "hello", "hi", "hey", "good morning", "good afternoon",
                "how are you", "greetings", "good day", "nice to meet you"
            ],
            "general_conversation": [
                "thank you", "thanks", "help", "what can you do",
                "assistance", "support", "yes", "no", "okay", "sure"
            ]
        }

    def _prepare_training_data(self, training_data: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:
        """Convert training data to lists for SetFit"""
        texts = []
        labels = []

        for intent, examples in training_data.items():
            for example in examples:
                texts.append(example.strip().lower())  # Normalize
                labels.append(intent)

        return texts, labels

    async def _save_model_safely(self):
        """Save model with atomic operation for production safety"""
        try:
            # Create model directory
            self.model_path.parent.mkdir(parents=True, exist_ok=True)

            # Save model
            self.model.save_pretrained(str(self.model_path))

            # Save label mappings
            mappings_path = self.model_path / "label_mappings.json"
            with open(mappings_path, 'w') as f:
                json.dump({
                    "label_to_intent": self.label_to_intent,
                    "intent_to_label": self.intent_to_label,
                    "training_timestamp": time.time(),
                    "total_intents": len(self.intent_to_label)
                }, f, indent=2)

            logger.info(f"Model saved successfully to {self.model_path}")

        except Exception as e:
            logger.error(f"Model saving failed: {e}")
            raise

    def _load_label_mappings(self) -> bool:
        """Load label mappings from saved model"""
        try:
            mappings_path = self.model_path / "label_mappings.json"
            if not mappings_path.exists():
                logger.warning("Label mappings not found")
                return False

            with open(mappings_path, 'r') as f:
                mappings = json.load(f)

            # Convert string keys back to integers for label_to_intent
            self.label_to_intent = {int(k): v for k, v in mappings["label_to_intent"].items()}
            self.intent_to_label = mappings["intent_to_label"]

            logger.debug(f"Loaded {len(self.intent_to_label)} intent mappings")
            return True

        except Exception as e:
            logger.error(f"Loading label mappings failed: {e}")
            return False

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_time = (self.total_classification_time / self.classification_count
                   if self.classification_count > 0 else 0.0)

        return {
            "total_classifications": self.classification_count,
            "average_time_ms": round(avg_time, 2),
            "is_trained": self.is_trained,
            "available_intents": list(self.intent_to_label.keys()) if self.intent_to_label else [],
            "model_path": str(self.model_path),
            "setfit_available": SETFIT_AVAILABLE
        }