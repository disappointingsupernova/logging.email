# Quick Start Guide

Get logging.email running locally in 10 minutes.

## Prerequisites

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+
- Git

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/logging.email.git
cd logging.email
```

### 2. Database Setup
```bash
mysql -u root -p
```

```sql
CREATE DATABASE logging_email_dev;
USE logging_email_dev;
SOURCE config/schema.sql;
```

### 3. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=logging_email_dev
REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=email_processing_dev
JWT_SECRET=$(openssl rand -hex 32)
API_TOKEN_SALT=$(openssl rand -hex 32)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_PRICE_ID=price_your_price
DOMAIN=localhost
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8080
ATTACHMENT_STORAGE_PATH=../attachments
EOF

# Start backend
python main.py
```

Backend now running at http://localhost:8000

### 4. Generate API Tokens
```bash
# In new terminal
cd config
python3 generate_tokens.py
```

Follow prompts and save the generated tokens.

### 5. Worker Setup
```bash
cd worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=logging_email_dev
REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=email_processing_dev
ATTACHMENT_STORAGE_PATH=../attachments
EOF

# Start worker
python worker.py
```

### 6. Frontend Setup
```bash
cd frontend
python3 -m http.server 8080
```

Frontend now running at http://localhost:8080

## Testing

### 1. Register Account
Open http://localhost:8080 and register with:
- Email: test@example.com
- Password: test123

### 2. Get Your Email Address
After registration, you'll see your default email address:
```
<uuid>@localhost
```

### 3. Simulate Email Reception

Since we're not running Postfix locally, we'll simulate email ingestion:

```bash
# Create test email file
cat > test_email.eml << EOF
From: sender@example.com
To: <your-uuid>@localhost
Subject: Test Email
Content-Type: text/plain

This is a test email body.
EOF

# Ingest via API
curl -X POST http://localhost:8000/ingest \
  -H "X-API-Token: YOUR_WORKER_TOKEN" \
  -F "recipient=<your-uuid>@localhost" \
  -F "sender=sender@example.com" \
  -F "size=100" \
  -F "raw_email=@test_email.eml"
```

### 4. View Message
Refresh the frontend - your test message should appear!

## Common Issues

### "Connection refused" to MySQL
- Ensure MySQL is running: `sudo systemctl start mysql`
- Check credentials in .env file

### "Connection refused" to Redis
- Ensure Redis is running: `sudo systemctl start redis`
- Check Redis URL in .env file

### Worker not processing messages
- Check Redis queue: `redis-cli LLEN email_processing_dev`
- Check worker logs for errors
- Verify database connection

### Frontend not loading
- Check browser console for errors
- Verify CORS settings in backend
- Ensure backend is running

## Next Steps

1. **Read the docs**:
   - [Deployment Guide](docs/DEPLOYMENT.md)
   - [Security Architecture](docs/SECURITY.md)
   - [API Documentation](docs/API.md)

2. **Set up Postfix** (for real email):
   - Follow [Deployment Guide](docs/DEPLOYMENT.md)
   - Configure MX records
   - Install policy service

3. **Configure Stripe**:
   - Create Stripe account
   - Get test API keys
   - Set up webhook endpoint

4. **Deploy to production**:
   - Provision servers
   - Configure TLS
   - Set up monitoring

## Development Workflow

### Running All Services
```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2: Worker
cd worker && source venv/bin/activate && python worker.py

# Terminal 3: Frontend
cd frontend && python -m http.server 8080

# Terminal 4: Redis (if not running as service)
redis-server

# Terminal 5: MySQL (if not running as service)
mysqld
```

### Making Changes

1. **Backend changes**: Restart backend service
2. **Worker changes**: Restart worker service
3. **Frontend changes**: Refresh browser
4. **Database changes**: Run migration SQL

### Testing Changes

```bash
# Backend tests
cd backend
pytest

# Worker tests
cd worker
pytest

# Integration test
./tests/test_email_flow.sh
```

## Useful Commands

```bash
# Check queue depth
redis-cli LLEN email_processing_dev

# View recent messages
mysql -u root -p logging_email_dev -e "SELECT * FROM messages ORDER BY received_at DESC LIMIT 5"

# Clear queue
redis-cli DEL email_processing_dev

# Reset database
mysql -u root -p logging_email_dev < config/schema.sql

# Generate new API token
python config/generate_tokens.py
```

## Getting Help

- Check [docs/](docs/) directory
- Review [SECURITY.md](docs/SECURITY.md) for security questions
- See [TESTING.md](docs/TESTING.md) for testing guidance
- Read [API.md](docs/API.md) for API reference

## Production Deployment

When ready for production:

1. Follow [DEPLOYMENT.md](docs/DEPLOYMENT.md)
2. Use strong secrets (not dev defaults)
3. Enable TLS everywhere
4. Configure monitoring
5. Set up backups
6. Review [SECURITY.md](docs/SECURITY.md)

Happy logging! 📧
