# 🔧 MongoDB E-commerce MCP Server - Troubleshooting Checklist

## 🚨 Quick Diagnosis Guide

### **Server Won't Start**
```bash
# 1. Check virtual environment
source .venv/bin/activate
which python  # Should show .venv path

# 2. Install missing dependencies
pip install 'pymongo[srv]>=4.14.0' pydantic[email] fastapi uvicorn

# 3. Check port availability
lsof -ti:8000 | xargs kill -9  # Kill existing process

# 4. Verify environment file
cat .env | grep ATLAS_URI
```

### **MongoDB Connection Failed**
```bash
# 1. Test connection manually
python -c "
import asyncio
from src.database.mongodb import mongodb_client

async def test():
    print('Testing MongoDB connection...')
    success = await mongodb_client.connect()
    print(f'Connection: {\"SUCCESS\" if success else \"FAILED\"}')
    if success:
        health = await mongodb_client.health_check()
        print(f'Health: {health}')
        await mongodb_client.disconnect()

asyncio.run(test())
"

# 2. Check Atlas URI format
# Should be: mongodb+srv://username:password@cluster.mongodb.net

# 3. Verify network connectivity
curl -X GET "https://httpbin.org/ip"
```

### **Import Errors**
```bash
# AsyncMongoClient not found
pip install --upgrade 'pymongo[srv]>=4.14.0'

# email-validator missing
pip install pydantic[email]

# Module not found errors
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
```

### **Database Seeding Issues**
```bash
# Clear and re-seed database
python -c "
import asyncio
from src.database.seeder import mongodb_seeder

async def reset():
    await mongodb_seeder.clear_all_data()
    await mongodb_seeder.seed_all()
    print('Database reset complete')

asyncio.run(reset())
"
```

### **API Endpoint Errors**
```bash
# Test health endpoint
curl -X GET "http://127.0.0.1:8000/health/"

# Test query endpoint
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello"}'

# Check API docs
open http://127.0.0.1:8000/docs
```

---

## 🔍 Error Code Reference

### **MongoDB Errors**
| Error | Cause | Solution |
|-------|-------|----------|
| `ServerSelectionTimeoutError` | Network/Auth issue | Check Atlas URI and whitelist IP |
| `ConfigurationError` | Invalid connection string | Verify ATLAS_URI format |
| `OperationFailure` | Authentication failed | Check username/password |

### **Python Errors**
| Error | Cause | Solution |
|-------|-------|----------|
| `ImportError: AsyncMongoClient` | Old PyMongo version | `pip install pymongo>=4.14.0` |
| `ModuleNotFoundError: email_validator` | Missing dependency | `pip install pydantic[email]` |
| `AttributeError: DATABASE_URL` | Wrong config | Use ATLAS_URI instead |

### **Server Errors**
| Error | Cause | Solution |
|-------|-------|----------|
| `Address already in use` | Port 8000 busy | Kill process or use different port |
| `Permission denied` | No write access | Check file permissions |
| `Command not found: uvicorn` | Not in venv | `source .venv/bin/activate` |

---

## 🛠️ Emergency Commands

### **Reset Everything**
```bash
# Kill all servers
pkill -f "uvicorn\|python.*main.py"

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +

# Restart server
.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### **Database Emergency Reset**
```bash
# WARNING: This will delete all data!
python -c "
import asyncio
from src.database.mongodb import mongodb_client

async def emergency_reset():
    db = mongodb_client.database
    await mongodb_client.connect()
    
    # Drop all collections
    for collection_name in ['products', 'customers', 'orders', 'inventory']:
        await db[collection_name].drop()
    
    print('All collections dropped!')
    await mongodb_client.disconnect()

asyncio.run(emergency_reset())
"
```

### **Log Analysis**
```bash
# Check server logs
tail -f logs/app.log

# Search for errors
grep -i "error\|exception\|failed" logs/app.log

# Check connection issues
grep -i "mongo\|database\|connection" logs/app.log
```

---

## 📞 When to Contact Support

### **Contact support if:**
- MongoDB Atlas cluster is down
- Persistent connection timeouts after network verification
- Unexpected data corruption
- Performance issues in production

### **Before contacting support, provide:**
1. Full error message and stack trace
2. Environment details (Python version, OS, dependencies)
3. Configuration (without sensitive credentials)
4. Steps to reproduce the issue
5. Relevant log excerpts

---

## ✅ Health Check Script

Create this as `health_check.py` for regular monitoring:

```python
#!/usr/bin/env python3
"""
MongoDB E-commerce MCP Server Health Check
Run this script to verify all systems are operational
"""

import asyncio
import sys
import requests
from datetime import datetime

async def check_mongodb():
    """Test MongoDB connection"""
    try:
        from src.database.mongodb import mongodb_client
        success = await mongodb_client.connect()
        if success:
            health = await mongodb_client.health_check()
            await mongodb_client.disconnect()
            return health.get("status") == "healthy"
        return False
    except Exception as e:
        print(f"MongoDB Error: {e}")
        return False

def check_server():
    """Test server endpoints"""
    try:
        response = requests.get("http://127.0.0.1:8000/health/", timeout=5)
        return response.status_code == 200 and response.json().get("status") == "healthy"
    except Exception as e:
        print(f"Server Error: {e}")
        return False

async def main():
    print(f"🔍 Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check MongoDB
    print("📊 Checking MongoDB connection...")
    mongo_ok = await check_mongodb()
    print(f"   Status: {'✅ HEALTHY' if mongo_ok else '❌ FAILED'}")
    
    # Check Server
    print("🌐 Checking server endpoints...")
    server_ok = check_server()
    print(f"   Status: {'✅ HEALTHY' if server_ok else '❌ FAILED'}")
    
    # Overall status
    overall = mongo_ok and server_ok
    print("=" * 50)
    print(f"🎯 Overall Status: {'✅ ALL SYSTEMS OPERATIONAL' if overall else '❌ ISSUES DETECTED'}")
    
    return 0 if overall else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

---

**Keep this checklist handy for quick issue resolution! 🚑**