# Implementation Guide

## 🚀 Step-by-Step Implementation

This guide provides detailed instructions for implementing the AI-powered intent classification system in your e-commerce application.

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- 4GB RAM minimum (8GB recommended)
- 2GB storage for models
- Redis server (for caching)

### Dependencies Installation
```bash
# Core ML dependencies
pip install setfit sentence-transformers torch transformers

# Additional utilities
pip install redis numpy scikit-learn pandas

# Optional: For GPU acceleration
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 🏗 Implementation Steps

### Step 1: Create Training Data

#### Define Intent Categories
```python
# src/data/intent_training_data.py
INTENT_TRAINING_DATA = {
    "inventory_inquiry": [
        "show me products",
        "list all items",
        "what products do you have",
        "display catalog",
        "product inventory",
        "five products list",
        "available items",
        "what's in stock",
        "show inventory",
        "product list",
        "give me products",
        "display products",
        "catalog items",
        "stock items",
        "merchandise list",
        "show me what you have"
    ],

    "sales_inquiry": [
        "what's my revenue",
        "sales data",
        "how much did I sell",
        "earnings report",
        "sales performance",
        "revenue analysis",
        "income data",
        "sales figures",
        "total sales",
        "monthly revenue",
        "sales metrics",
        "financial performance",
        "revenue report",
        "sales summary",
        "earnings data",
        "profit information"
    ],

    "customer_inquiry": [
        "top customers",
        "customer data",
        "buyer information",
        "client details",
        "customer analytics",
        "best customers",
        "customer insights",
        "customer list",
        "buyer data",
        "customer metrics",
        "client analytics",
        "customer demographics",
        "buyer statistics",
        "customer behavior",
        "client information",
        "customer profiles"
    ],

    "order_inquiry": [
        "recent orders",
        "order status",
        "pending orders",
        "order history",
        "purchase data",
        "order details",
        "order information",
        "order analytics",
        "order summary",
        "purchase history",
        "order metrics",
        "fulfillment status",
        "shipping data",
        "order tracking",
        "purchase orders",
        "order reports"
    ],

    "analytics_inquiry": [
        "analyze trends",
        "business insights",
        "performance metrics",
        "trend analysis",
        "business analytics",
        "performance data",
        "insights report",
        "trend report",
        "analytics dashboard",
        "business performance",
        "performance analysis",
        "business metrics",
        "trend insights",
        "analytical data",
        "performance insights",
        "business intelligence"
    ],

    "greeting": [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "what's up",
        "greetings",
        "hey there",
        "hello there",
        "hi there",
        "good day",
        "howdy",
        "nice to meet you",
        "pleasure to meet you"
    ],

    "general_conversation": [
        "thank you",
        "thanks",
        "appreciate it",
        "can you help",
        "need help",
        "what can you do",
        "how does this work",
        "what are you",
        "who are you",
        "help me",
        "assistance needed",
        "support",
        "yes",
        "no",
        "okay",
        "sure"
    ]
}
```

### Step 2: Create Intent Classifier Classes

#### Base Intent Classifier
```python
# src/services/intent_classification/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional
import time

@dataclass
class IntentResult:
    """Result of intent classification"""
    intent: str
    confidence: float
    method: str
    processing_time: float
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "method": self.method,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp
        }

class BaseIntentClassifier(ABC):
    """Base class for all intent classifiers"""

    @abstractmethod
    def classify(self, query: str) -> IntentResult:
        """Classify user query into intent"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if classifier is ready for use"""
        pass
```

#### SetFit Classifier Implementation
```python
# src/services/intent_classification/setfit_classifier.py
import time
import logging
from typing import Tuple, Optional, List
import numpy as np
from setfit import SetFitModel, SetFitTrainer
from sentence_transformers.losses import CosineSimilarityLoss
from datasets import Dataset

from .base import BaseIntentClassifier, IntentResult

logger = logging.getLogger(__name__)

class SetFitClassifier(BaseIntentClassifier):
    """SetFit-based intent classifier"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None
        self.label_mapping = {}
        self.reverse_label_mapping = {}
        self._is_trained = False

    def train(self, training_data: dict, save_path: str = None) -> bool:
        """Train SetFit model on provided data"""
        try:
            logger.info("Starting SetFit model training...")

            # Prepare training data
            texts, labels = self._prepare_training_data(training_data)

            # Create label mappings
            unique_labels = list(set(labels))
            self.label_mapping = {i: label for i, label in enumerate(unique_labels)}
            self.reverse_label_mapping = {label: i for i, label in enumerate(unique_labels)}

            # Convert labels to integers
            numeric_labels = [self.reverse_label_mapping[label] for label in labels]

            # Create dataset
            train_dataset = Dataset.from_dict({
                "text": texts,
                "label": numeric_labels
            })

            # Initialize model
            self.model = SetFitModel.from_pretrained(
                "sentence-transformers/paraphrase-mpnet-base-v2",
                labels=list(self.label_mapping.keys())
            )

            # Create trainer
            trainer = SetFitTrainer(
                model=self.model,
                train_dataset=train_dataset,
                loss_class=CosineSimilarityLoss,
                num_iterations=20,  # Few iterations for few-shot learning
                num_epochs=1
            )

            # Train the model
            trainer.train()

            # Save model if path provided
            if save_path:
                self.model.save_pretrained(save_path)
                # Save label mappings
                import json
                with open(f"{save_path}/label_mapping.json", "w") as f:
                    json.dump(self.label_mapping, f)
                logger.info(f"Model saved to {save_path}")

            self._is_trained = True
            logger.info("SetFit model training completed successfully")
            return True

        except Exception as e:
            logger.error(f"SetFit training failed: {e}", exc_info=True)
            return False

    def _prepare_training_data(self, training_data: dict) -> Tuple[List[str], List[str]]:
        """Convert training data to flat lists"""
        texts = []
        labels = []

        for intent, examples in training_data.items():
            for example in examples:
                texts.append(example)
                labels.append(intent)

        return texts, labels

    def load(self, model_path: str) -> bool:
        """Load pre-trained SetFit model"""
        try:
            import json
            import os

            # Load model
            self.model = SetFitModel.from_pretrained(model_path)

            # Load label mappings
            label_path = os.path.join(model_path, "label_mapping.json")
            if os.path.exists(label_path):
                with open(label_path, "r") as f:
                    # Convert string keys back to integers
                    loaded_mapping = json.load(f)
                    self.label_mapping = {int(k): v for k, v in loaded_mapping.items()}
                    self.reverse_label_mapping = {v: k for k, v in self.label_mapping.items()}

            self._is_trained = True
            logger.info(f"SetFit model loaded from {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load SetFit model: {e}", exc_info=True)
            return False

    def classify(self, query: str) -> IntentResult:
        """Classify query using SetFit model"""
        start_time = time.time()

        try:
            if not self.is_available():
                raise RuntimeError("SetFit model not available")

            # Get prediction probabilities
            probs = self.model.predict_proba([query])[0]

            # Get highest confidence prediction
            predicted_label = int(np.argmax(probs))
            confidence = float(probs[predicted_label])

            intent = self.label_mapping[predicted_label]
            processing_time = (time.time() - start_time) * 1000  # Convert to ms

            return IntentResult(
                intent=intent,
                confidence=confidence,
                method="setfit",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"SetFit classification failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            return IntentResult(
                intent="general_inquiry",
                confidence=0.0,
                method="setfit_error",
                processing_time=processing_time
            )

    def is_available(self) -> bool:
        """Check if SetFit model is ready"""
        return self.model is not None and self._is_trained
```

#### Similarity-Based Classifier (Fallback)
```python
# src/services/intent_classification/similarity_classifier.py
import time
import logging
from typing import Dict, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .base import BaseIntentClassifier, IntentResult

logger = logging.getLogger(__name__)

class SimilarityClassifier(BaseIntentClassifier):
    """Sentence-BERT similarity-based classifier"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.intent_embeddings = {}
        self.intent_examples = {}
        self.threshold = 0.7

    def initialize(self, intent_examples: Dict[str, List[str]]) -> bool:
        """Initialize model and compute intent embeddings"""
        try:
            logger.info("Initializing Similarity classifier...")

            # Load sentence transformer model
            self.model = SentenceTransformer(self.model_name)

            # Store examples
            self.intent_examples = intent_examples

            # Compute embeddings for all intent examples
            for intent, examples in intent_examples.items():
                embeddings = self.model.encode(examples)
                # Use mean embedding as intent representation
                self.intent_embeddings[intent] = np.mean(embeddings, axis=0)

            logger.info("Similarity classifier initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize similarity classifier: {e}")
            return False

    def classify(self, query: str) -> IntentResult:
        """Classify query using similarity matching"""
        start_time = time.time()

        try:
            if not self.is_available():
                raise RuntimeError("Similarity classifier not available")

            # Encode query
            query_embedding = self.model.encode([query])[0]

            # Calculate similarities with all intents
            best_intent = "general_inquiry"
            best_score = 0.0

            for intent, intent_embedding in self.intent_embeddings.items():
                similarity = cosine_similarity(
                    [query_embedding],
                    [intent_embedding]
                )[0][0]

                if similarity > best_score:
                    best_score = similarity
                    best_intent = intent

            # Apply threshold
            if best_score < self.threshold:
                best_intent = "general_inquiry"
                best_score = 0.5

            processing_time = (time.time() - start_time) * 1000

            return IntentResult(
                intent=best_intent,
                confidence=float(best_score),
                method="similarity",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Similarity classification failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            return IntentResult(
                intent="general_inquiry",
                confidence=0.0,
                method="similarity_error",
                processing_time=processing_time
            )

    def is_available(self) -> bool:
        """Check if similarity classifier is ready"""
        return (self.model is not None and
                len(self.intent_embeddings) > 0)
```

### Step 3: Production Intent Classifier

```python
# src/services/intent_classification/production_classifier.py
import time
import logging
from typing import Optional
import redis
import json
import hashlib

from .setfit_classifier import SetFitClassifier
from .similarity_classifier import SimilarityClassifier
from .base import IntentResult

logger = logging.getLogger(__name__)

class ProductionIntentClassifier:
    """Production-ready intent classifier with caching and fallbacks"""

    def __init__(self,
                 setfit_model_path: Optional[str] = None,
                 redis_config: Optional[dict] = None,
                 cache_ttl: int = 3600):

        # Initialize classifiers
        self.setfit_classifier = SetFitClassifier(setfit_model_path)
        self.similarity_classifier = SimilarityClassifier()

        # Initialize cache
        self.cache = None
        self.cache_ttl = cache_ttl
        if redis_config:
            try:
                self.cache = redis.Redis(**redis_config)
                self.cache.ping()  # Test connection
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis cache initialization failed: {e}")

        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "setfit_success": 0,
            "similarity_fallback": 0,
            "errors": 0
        }

    def initialize(self, training_data: dict, setfit_model_path: str = None) -> bool:
        """Initialize both classifiers"""
        success = True

        # Initialize similarity classifier (always works)
        if not self.similarity_classifier.initialize(training_data):
            logger.error("Failed to initialize similarity classifier")
            success = False

        # Try to load or train SetFit model
        if setfit_model_path and self.setfit_classifier.load(setfit_model_path):
            logger.info("SetFit model loaded successfully")
        else:
            logger.info("Training new SetFit model...")
            model_save_path = setfit_model_path or "./models/setfit_intent_classifier"
            if self.setfit_classifier.train(training_data, model_save_path):
                logger.info("SetFit model trained successfully")
            else:
                logger.warning("SetFit training failed, will use similarity fallback")
                success = False

        return success

    def classify(self, query: str) -> IntentResult:
        """Main classification method with caching and fallbacks"""
        start_time = time.time()
        self.stats["total_queries"] += 1

        # Step 1: Check cache
        cached_result = self._get_from_cache(query)
        if cached_result:
            self.stats["cache_hits"] += 1
            return cached_result

        # Step 2: Try SetFit classification
        if self.setfit_classifier.is_available():
            try:
                result = self.setfit_classifier.classify(query)
                if result.confidence > 0.8:
                    self.stats["setfit_success"] += 1
                    self._cache_result(query, result)
                    return result
            except Exception as e:
                logger.warning(f"SetFit classification failed: {e}")

        # Step 3: Fallback to similarity classification
        try:
            result = self.similarity_classifier.classify(query)
            self.stats["similarity_fallback"] += 1

            # Cache even fallback results if confidence is reasonable
            if result.confidence > 0.7:
                self._cache_result(query, result)

            return result

        except Exception as e:
            logger.error(f"All classification methods failed: {e}")
            self.stats["errors"] += 1

            # Ultimate fallback
            processing_time = (time.time() - start_time) * 1000
            return IntentResult(
                intent="general_inquiry",
                confidence=0.0,
                method="fallback",
                processing_time=processing_time
            )

    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        normalized = query.lower().strip()
        return f"intent:{hashlib.md5(normalized.encode()).hexdigest()}"

    def _get_from_cache(self, query: str) -> Optional[IntentResult]:
        """Retrieve result from cache"""
        if not self.cache:
            return None

        try:
            cache_key = self._get_cache_key(query)
            cached = self.cache.get(cache_key)
            if cached:
                data = json.loads(cached.decode())
                return IntentResult(**data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    def _cache_result(self, query: str, result: IntentResult):
        """Store result in cache"""
        if not self.cache:
            return

        try:
            cache_key = self._get_cache_key(query)
            data = result.to_dict()
            self.cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

    def get_stats(self) -> dict:
        """Get classifier performance statistics"""
        if self.stats["total_queries"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_queries"]
            setfit_success_rate = self.stats["setfit_success"] / self.stats["total_queries"]
            fallback_rate = self.stats["similarity_fallback"] / self.stats["total_queries"]
            error_rate = self.stats["errors"] / self.stats["total_queries"]
        else:
            cache_hit_rate = setfit_success_rate = fallback_rate = error_rate = 0.0

        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "setfit_success_rate": setfit_success_rate,
            "fallback_rate": fallback_rate,
            "error_rate": error_rate
        }
```

### Step 4: Integration with Query Processor

```python
# src/services/query_processor.py (modifications)
from src.services.intent_classification.production_classifier import ProductionIntentClassifier
from src.data.intent_training_data import INTENT_TRAINING_DATA

class QueryProcessor:
    def __init__(self):
        # Initialize intent classifier
        self.intent_classifier = ProductionIntentClassifier(
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "decode_responses": False
            }
        )

        # Initialize with training data
        self.intent_classifier.initialize(
            training_data=INTENT_TRAINING_DATA,
            setfit_model_path="./models/setfit_intent_classifier"
        )

        # Rest of existing initialization...
        self._token_usage = None
        # ... (keep existing code)

    def _classify_intent(self, query: str) -> str:
        """AI-powered intent classification (REPLACED)"""
        try:
            # Use new AI classifier
            result = self.intent_classifier.classify(query)

            # Log classification for monitoring
            logger.info(f"Intent classified: {result.intent} "
                       f"(confidence: {result.confidence:.2f}, "
                       f"method: {result.method})")

            return result.intent

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Fallback to existing regex patterns
            return self._classify_intent_regex(query)

    def _classify_intent_regex(self, query: str) -> str:
        """Fallback regex classification (KEEP as backup)"""
        query_lower = query.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return "general_inquiry"

    # Add method to get classification stats
    def get_classification_stats(self) -> dict:
        """Get intent classification performance stats"""
        return self.intent_classifier.get_stats()
```

## 🎯 Testing the Implementation

### Basic Testing
```python
# test_intent_classification.py
from src.services.intent_classification.production_classifier import ProductionIntentClassifier
from src.data.intent_training_data import INTENT_TRAINING_DATA

def test_intent_classification():
    # Initialize classifier
    classifier = ProductionIntentClassifier()
    classifier.initialize(INTENT_TRAINING_DATA)

    # Test cases
    test_cases = [
        ("show me my products", "inventory_inquiry"),
        ("what's my revenue?", "sales_inquiry"),
        ("top customers", "customer_inquiry"),
        ("recent orders", "order_inquiry"),
        ("analyze trends", "analytics_inquiry"),
        ("hello", "greeting"),
        ("thank you", "general_conversation")
    ]

    print("Testing Intent Classification:")
    print("-" * 50)

    for query, expected in test_cases:
        result = classifier.classify(query)
        status = "✅" if result.intent == expected else "❌"

        print(f"{status} Query: '{query}'")
        print(f"   Expected: {expected}")
        print(f"   Got: {result.intent} (confidence: {result.confidence:.2f})")
        print(f"   Method: {result.method}")
        print()

if __name__ == "__main__":
    test_intent_classification()
```

### Performance Testing
```python
# performance_test.py
import time
from src.services.intent_classification.production_classifier import ProductionIntentClassifier
from src.data.intent_training_data import INTENT_TRAINING_DATA

def performance_test():
    classifier = ProductionIntentClassifier()
    classifier.initialize(INTENT_TRAINING_DATA)

    test_queries = [
        "show me products",
        "what's my revenue",
        "top customers",
        "recent orders"
    ] * 100  # Test with 400 queries

    start_time = time.time()

    for query in test_queries:
        result = classifier.classify(query)

    total_time = time.time() - start_time
    avg_time = (total_time / len(test_queries)) * 1000  # ms

    print(f"Performance Test Results:")
    print(f"Total queries: {len(test_queries)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per query: {avg_time:.2f}ms")

    # Print stats
    stats = classifier.get_stats()
    print(f"\nClassification Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    performance_test()
```

## 🔧 Configuration

### Environment Configuration
```bash
# .env additions
INTENT_CLASSIFICATION_MODEL_PATH=./models/setfit_intent_classifier
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
INTENT_CACHE_TTL=3600
```

### Model Directory Structure
```
models/
└── setfit_intent_classifier/
    ├── config.json
    ├── model.safetensors
    ├── tokenizer.json
    ├── label_mapping.json
    └── training_args.bin
```

## 📊 Monitoring Integration

### Add to Query Processor Response
```python
# In query_processor.py, add to metadata
metadata = {
    "model_used": model_manager.active_model,
    "execution_time_ms": int(execution_time),
    "tools_called": [tc["tool"] for tc in tool_calls],
    "confidence_score": self._calculate_confidence(intent, entities, tool_results),
    "query_intent": intent,
    "extracted_entities": list(entities.keys()) if entities else [],

    # NEW: Intent classification info
    "intent_classification": {
        "method": result.method,
        "confidence": result.confidence,
        "processing_time": result.processing_time
    }
}
```

## ✅ Verification Checklist

- [ ] All dependencies installed
- [ ] Training data prepared
- [ ] SetFit classifier implemented
- [ ] Similarity classifier implemented
- [ ] Production classifier with caching
- [ ] Integration with query processor
- [ ] Basic testing completed
- [ ] Performance testing completed
- [ ] Redis cache configured
- [ ] Monitoring integration added

---
*Implementation Guide Version: 1.0*
*Last Updated: September 2025*