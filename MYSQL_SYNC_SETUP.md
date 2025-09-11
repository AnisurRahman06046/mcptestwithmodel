# MySQL-MongoDB Sync Setup Guide

This guide walks you through setting up the MySQL-MongoDB synchronization system in your project.

## Overview

The sync system automatically discovers tables in your MySQL database and syncs data to MongoDB. It supports:

- **Automatic table discovery** - No need to know table names beforehand
- **Incremental sync** - Only syncs new/updated records
- **Intelligent mapping** - Maps MySQL data to MongoDB format
- **RESTful API control** - Full control via HTTP endpoints
- **Scheduled sync** - Automatic background synchronization

## Prerequisites

1. **MySQL Database** - Your source database with tables to sync
2. **MongoDB Atlas** - Your target MongoDB database (already configured)
3. **Python dependencies** - Install required packages

```bash
pip install aiomysql
```

## Setup Steps

### 1. Configure MySQL Connection

Add these variables to your `.env` file:

```bash
# MySQL Connection Details
MYSQL_HOST=your-mysql-host-here
MYSQL_PORT=3306
MYSQL_USER=your-mysql-username
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=your-database-name
MYSQL_CHARSET=utf8mb4

# Sync Configuration
SYNC_ENABLED=true
SYNC_INTERVAL_MINUTES=60
SYNC_BATCH_SIZE=1000
SYNC_ONLY_TIMESTAMP_TABLES=true
```

### 2. Discover Available Tables

Run the table discovery script to see what's available:

```bash
python list_tables.py
```

This will show output like:
```
Found 12 tables:
  ✅ products      (has timestamps - sync ready)
  ✅ orders        (has timestamps - sync ready)  
  ✅ customers     (has timestamps - sync ready)
  ⚠️  categories   (no timestamps)
  ✅ inventory     (has timestamps - sync ready)
```

### 3. Configure Which Tables to Sync

**Option A: Sync all timestamp-enabled tables automatically**
```bash
SYNC_ONLY_TIMESTAMP_TABLES=true
# No need to specify SYNC_TABLES
```

**Option B: Sync specific tables**
```bash
SYNC_TABLES=products,orders,customers,inventory
SYNC_ONLY_TIMESTAMP_TABLES=false
```

### 4. Start Your Application

The sync system integrates with your existing FastAPI application:

```bash
python -m uvicorn src.main:app --reload
```

### 5. Access Sync API

The sync endpoints are available at:

- **Status**: `GET /sync/status` - Current sync status
- **Discover**: `GET /sync/tables` - List all available tables
- **Trigger**: `POST /sync/trigger` - Manual sync
- **Health**: `GET /sync/health` - Connection health

## API Usage Examples

### Check Sync Status
```bash
curl http://localhost:8000/sync/status
```

### Discover Tables
```bash
curl http://localhost:8000/sync/tables
```

### Trigger Manual Sync
```bash
curl -X POST http://localhost:8000/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "tables": ["products", "orders"],
    "force_full_sync": false
  }'
```

### Start Automatic Scheduler
```bash
curl -X POST http://localhost:8000/sync/scheduler/start
```

### Update Sync Interval
```bash
curl -X PUT http://localhost:8000/sync/scheduler \
  -H "Content-Type: application/json" \
  -d '{"interval_minutes": 30}'
```

## Data Mapping

The system intelligently maps MySQL tables to MongoDB collections:

### Automatic Detection
- **Products**: Tables with columns like `name`, `price`, `sku`, `category`
- **Customers**: Tables with `email` and `name`/`first_name` columns  
- **Orders**: Tables with `customer_id`, `total`/`amount`, `status`
- **Inventory**: Tables with `product_id`, `quantity`, `stock`

### Data Transformations
- **IDs**: MySQL IDs become MongoDB `_id` fields
- **Timestamps**: `created_at`, `updated_at` columns are preserved
- **Types**: Decimal → Float, JSON strings → Objects
- **Names**: `first_name` + `last_name` → `name`

### Example Mapping

**MySQL `products` table:**
```sql
id | name | price | sku | created_at | updated_at
1  | iPhone | 999.99 | APPLE-IP-14 | 2024-01-01 | 2024-01-02
```

**MongoDB `products` collection:**
```json
{
  "_id": "1",
  "name": "iPhone",
  "price": 999.99,
  "sku": "APPLE-IP-14",
  "category": "Electronics",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

## Monitoring & Troubleshooting

### View Sync Logs
```bash
tail -f logs/sync/*.log
```

### Check Connection Health
```bash
curl http://localhost:8000/sync/health
```

### Reset Sync (Force Full Sync)
```bash
# Reset specific table
curl -X POST http://localhost:8000/sync/reset/products

# Reset all tables
curl -X POST http://localhost:8000/sync/reset-all
```

### Pause/Resume Sync
```bash
# Pause
curl -X POST http://localhost:8000/sync/scheduler/pause

# Resume  
curl -X POST http://localhost:8000/sync/scheduler/resume
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MYSQL_HOST` | - | MySQL server hostname |
| `MYSQL_PORT` | 3306 | MySQL server port |
| `MYSQL_USER` | - | MySQL username |
| `MYSQL_PASSWORD` | - | MySQL password |
| `MYSQL_DATABASE` | - | MySQL database name |
| `SYNC_ENABLED` | false | Enable sync system |
| `SYNC_INTERVAL_MINUTES` | 60 | Auto-sync interval |
| `SYNC_BATCH_SIZE` | 1000 | Records per batch |
| `SYNC_TABLES` | null | Specific tables (comma-separated) |
| `SYNC_ONLY_TIMESTAMP_TABLES` | true | Only sync tables with timestamps |

### Sync Strategies

**Incremental Sync (Recommended)**
- Uses `created_at`/`updated_at` columns
- Only syncs new/modified records
- Fast and efficient

**Full Sync**
- Syncs all records every time
- Use for tables without timestamps
- Slower but comprehensive

## Common Issues

### 1. Connection Failed
```
Error: Failed to connect to MySQL
```
**Solution**: Check MySQL host, port, credentials in `.env`

### 2. No Tables Found
```
Found 0 tables
```
**Solution**: Verify database name and user permissions

### 3. No Timestamp Columns
```
Found 0 sync-ready tables
```
**Solution**: Either:
- Add `created_at`/`updated_at` columns to tables
- Set `SYNC_ONLY_TIMESTAMP_TABLES=false`

### 4. Sync Errors
```
Error syncing table: ...
```
**Solution**: Check logs and verify data types are compatible

## Security Considerations

1. **Credentials**: Store MySQL credentials in `.env`, not in code
2. **Network**: Use SSL connections for production
3. **Permissions**: MySQL user should have minimal required permissions
4. **Monitoring**: Monitor sync logs for suspicious activity

## Performance Tips

1. **Indexes**: Add indexes on timestamp columns (`created_at`, `updated_at`)
2. **Batch Size**: Adjust `SYNC_BATCH_SIZE` based on record size
3. **Interval**: Set appropriate `SYNC_INTERVAL_MINUTES` for your data velocity
4. **Tables**: Only sync tables you actually need

## Next Steps

1. **Test the sync** with a small table first
2. **Monitor performance** and adjust batch sizes
3. **Set up alerting** for sync failures
4. **Schedule regular health checks**

For more details, see the [MYSQL_MONGODB_SYNC_DOCUMENTATION.md](./MYSQL_MONGODB_SYNC_DOCUMENTATION.md) file.