import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "uptime" in data
    assert "database_connected" in data
    assert "model_loaded" in data
    assert "version" in data


def test_models_status_endpoint():
    """Test the models status endpoint"""
    response = client.get("/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "system_resources" in data
    assert len(data["models"]) > 0


def test_tools_list_endpoint():
    """Test the tools list endpoint"""
    response = client.get("/tools/list")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) > 0
    
    # Check that expected tools are present
    tool_names = [tool["name"] for tool in data["tools"]]
    expected_tools = ["get_sales_data", "get_inventory_status", "get_customer_info", "get_order_details"]
    for tool in expected_tools:
        assert tool in tool_names


def test_query_endpoint_sales():
    """Test the query endpoint with a sales query"""
    response = client.post("/query", json={
        "query": "What were our sales last month?",
        "context": {
            "user_id": "test_user",
            "shop_id": "test_shop"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "response" in data
    assert "metadata" in data
    assert data["metadata"]["execution_time_ms"] > 0


def test_query_endpoint_inventory():
    """Test the query endpoint with an inventory query"""
    response = client.post("/query", json={
        "query": "Which products are low on stock?",
        "context": {
            "user_id": "test_user",
            "shop_id": "test_shop"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "response" in data
    assert "metadata" in data


def test_query_endpoint_invalid():
    """Test the query endpoint with invalid input"""
    response = client.post("/query", json={})
    assert response.status_code == 422  # Validation error


def test_model_load_endpoint():
    """Test the model loading endpoint"""
    response = client.post("/models/load/llama3-7b")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "status" in data


def test_model_load_invalid():
    """Test loading an invalid model"""
    response = client.post("/models/load/invalid-model")
    assert response.status_code == 400  # Bad request
    data = response.json()
    assert "detail" in data


def test_model_unload_endpoint():
    """Test the model unloading endpoint"""
    # First load a model
    client.post("/models/load/llama3-7b")
    
    # Then unload it
    response = client.delete("/models/unload/llama3-7b")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "status" in data


class TestQueryProcessing:
    """Test query processing functionality"""
    
    def test_sales_query_processing(self):
        """Test sales query processing"""
        response = client.post("/query", json={
            "query": "How much revenue did we generate last month from electronics?",
            "context": {"user_id": "test", "shop_id": "test"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "sales" in data["response"].lower() or "revenue" in data["response"].lower()
    
    def test_inventory_query_processing(self):
        """Test inventory query processing"""
        response = client.post("/query", json={
            "query": "Show me products with low inventory levels",
            "context": {"user_id": "test", "shop_id": "test"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "inventory" in data["response"].lower() or "stock" in data["response"].lower()
    
    def test_customer_query_processing(self):
        """Test customer query processing"""
        response = client.post("/query", json={
            "query": "Who are my best customers?",
            "context": {"user_id": "test", "shop_id": "test"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "customer" in data["response"].lower()
    
    def test_order_query_processing(self):
        """Test order query processing"""
        response = client.post("/query", json={
            "query": "How many pending orders do I have?",
            "context": {"user_id": "test", "shop_id": "test"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "order" in data["response"].lower() or "pending" in data["response"].lower()


class TestResponseFormat:
    """Test response format consistency"""
    
    def test_query_response_structure(self):
        """Test that query responses have consistent structure"""
        response = client.post("/query", json={
            "query": "Test query",
            "context": {"user_id": "test"}
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "response" in data
        assert "metadata" in data
        
        # Check metadata structure
        metadata = data["metadata"]
        assert "model_used" in metadata
        assert "execution_time_ms" in metadata
        assert "tools_called" in metadata
        assert "confidence_score" in metadata
        
        # Check types
        assert isinstance(metadata["execution_time_ms"], int)
        assert isinstance(metadata["tools_called"], list)
        assert isinstance(metadata["confidence_score"], float)
        assert 0 <= metadata["confidence_score"] <= 1
    
    def test_error_response_structure(self):
        """Test error response structure"""
        response = client.post("/query", json={
            "query": "",  # Empty query should cause some processing issues
            "context": {"user_id": "test"}
        })
        assert response.status_code == 200  # API should handle gracefully
        data = response.json()
        
        # Even error responses should have basic structure
        assert "success" in data
        assert "response" in data
        assert "metadata" in data


if __name__ == "__main__":
    pytest.main([__file__])