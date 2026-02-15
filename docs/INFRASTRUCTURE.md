# Redis Caching & RabbitMQ Queuing

## Overview

- **Redis**: Caching for policy checks (reduce database load)
- **RabbitMQ**: Reliable message queuing for email processing

## Architecture

```
Policy Check → Redis Cache → Database (if cache miss)
                  ↓
            Cache Hit (fast)

Email Ingest → RabbitMQ Queue → Worker → Database
                  ↓
            Persistent Queue
```

## Redis Caching

### Purpose
Reduce database load on policy checks by caching recipient validation results.

### Cache Keys
- `policy:{email_address}` - Policy check results

### TTL (Time To Live)
- **OK responses**: 300 seconds (5 minutes)
- **REJECT responses**: 60 seconds (1 minute)

### Cache Invalidation
Cache is invalidated when:
- Email address is created/updated/deleted
- Customer tier changes
- Message is processed (rate limit check)

### Configuration
```env
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300
```

### Benefits
- **Performance**: Policy checks ~100x faster
- **Scalability**: Handles high email volume
- **Database protection**: Reduces load on MySQL

### Cache Flow

**First request (cache miss):**
```
1. Policy check for user@logging.email
2. Redis cache miss
3. Query database
4. Cache result (TTL: 300s)
5. Return OK/REJECT
```

**Subsequent requests (cache hit):**
```
1. Policy check for user@logging.email
2. Redis cache hit
3. Return cached OK/REJECT (no database query)
```

## RabbitMQ Queuing

### Purpose
Reliable, persistent message queue for email processing.

### Why RabbitMQ over Redis?
- **Persistence**: Messages survive restarts
- **Acknowledgements**: Guaranteed processing
- **Reliability**: No message loss
- **Scalability**: Multiple workers

### Queue Configuration
```env
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_QUEUE=email_processing
```

### Message Format
```json
{
  "message_id": 12345,
  "email_data": "From: sender@example.com..."
}
```

### Queue Properties
- **Durable**: Queue survives broker restart
- **Persistent**: Messages written to disk
- **Acknowledgement**: Manual ack after processing
- **Prefetch**: 1 message per worker

### Processing Flow

```
1. Email arrives at Postfix
2. Postfix forwards to backend /ingest
3. Backend creates Message record (is_processed=FALSE)
4. Backend publishes to RabbitMQ queue
5. Worker consumes message
6. Worker parses and sanitises email
7. Worker updates Message record (is_processed=TRUE)
8. Worker acknowledges message
9. RabbitMQ removes message from queue
```

### Failure Handling

**Worker crashes:**
- Message not acknowledged
- RabbitMQ requeues message
- Another worker processes it

**Database error:**
- Worker marks message as processed (avoid infinite retry)
- Logs error for investigation

## Installation

### Redis

```bash
# Ubuntu
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify
redis-cli ping  # Should return PONG
```

### RabbitMQ

```bash
# Ubuntu
sudo apt install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Verify
sudo rabbitmqctl status

# Enable management UI (optional)
sudo rabbitmq-plugins enable rabbitmq_management
# Access at http://localhost:15672 (guest/guest)
```

## Configuration

### Backend .env

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=logging_email
DB_PASSWORD=your_password
DB_NAME=logging_email

# RabbitMQ (Message Queue)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_QUEUE=email_processing

# Redis (Cache)
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300
```

### Worker .env

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=logging_email
DB_PASSWORD=your_password
DB_NAME=logging_email

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_QUEUE=email_processing

# Redis (for cache invalidation)
REDIS_URL=redis://localhost:6379/0

# Storage
ATTACHMENT_STORAGE_PATH=/var/lib/logging-email/attachments
```

## Monitoring

### Redis

```bash
# Check connection
redis-cli ping

# Monitor commands
redis-cli monitor

# Get cache stats
redis-cli info stats

# Check specific key
redis-cli get "policy:user@logging.email"

# List all policy keys
redis-cli keys "policy:*"

# Clear all cache
redis-cli flushdb
```

### RabbitMQ

```bash
# Check status
sudo rabbitmqctl status

# List queues
sudo rabbitmqctl list_queues

# Check queue depth
sudo rabbitmqctl list_queues name messages

# Purge queue (careful!)
sudo rabbitmqctl purge_queue email_processing
```

### Management UI

Access RabbitMQ management at http://localhost:15672
- Username: guest
- Password: guest

View:
- Queue depth
- Message rates
- Consumer count
- Memory usage

## Performance Tuning

### Redis

```bash
# Increase max memory
sudo nano /etc/redis/redis.conf
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru

sudo systemctl restart redis-server
```

### RabbitMQ

```bash
# Increase file descriptors
sudo nano /etc/default/rabbitmq-server
# Add: ulimit -n 65536

sudo systemctl restart rabbitmq-server
```

### Worker Scaling

Run multiple workers for parallel processing:

```bash
# Terminal 1
python worker.py

# Terminal 2
python worker.py

# Terminal 3
python worker.py
```

Each worker processes messages independently.

## Cache Invalidation

### Manual Invalidation

```python
from cache import cache_delete, cache_delete_pattern

# Invalidate specific address
cache_delete("policy:user@logging.email")

# Invalidate all policy cache
cache_delete_pattern("policy:*")
```

### Automatic Invalidation

Cache is automatically invalidated when:

**Address changes:**
```python
# In api.py when creating/deleting address
cache_delete(f"policy:{address}")
```

**Message processed:**
```python
# In worker.py after processing
cache_delete(f"policy:{email_address.address}")
```

## Troubleshooting

### Redis Connection Failed

```bash
# Check Redis running
sudo systemctl status redis-server

# Check connection
redis-cli ping

# Check logs
sudo journalctl -u redis-server -f
```

### RabbitMQ Connection Failed

```bash
# Check RabbitMQ running
sudo systemctl status rabbitmq-server

# Check logs
sudo journalctl -u rabbitmq-server -f

# Check port
sudo netstat -tlnp | grep 5672
```

### Messages Not Processing

```bash
# Check queue depth
sudo rabbitmqctl list_queues

# Check worker running
ps aux | grep worker.py

# Check worker logs
sudo journalctl -u worker -f
```

### Cache Not Working

```bash
# Test cache
redis-cli set test "value"
redis-cli get test

# Check backend can connect
python -c "import redis; r=redis.from_url('redis://localhost:6379/0'); print(r.ping())"
```

## Security

### Redis

```bash
# Bind to localhost only
sudo nano /etc/redis/redis.conf
# Set: bind 127.0.0.1

# Require password
# Set: requirepass your_strong_password

sudo systemctl restart redis-server
```

Update .env:
```env
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

### RabbitMQ

```bash
# Create dedicated user
sudo rabbitmqctl add_user logging_email strong_password
sudo rabbitmqctl set_permissions -p / logging_email ".*" ".*" ".*"

# Delete guest user (production)
sudo rabbitmqctl delete_user guest
```

Update .env:
```env
RABBITMQ_URL=amqp://logging_email:strong_password@localhost:5672/
```

## Summary

✅ **Redis caching** - Fast policy checks, reduced database load
✅ **RabbitMQ queuing** - Reliable message processing, no data loss
✅ **Cache invalidation** - Automatic on data changes
✅ **Scalable** - Multiple workers, high throughput
✅ **Monitored** - Management UI and CLI tools

Email processing is now fast, reliable, and scalable!
