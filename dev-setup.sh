#!/bin/bash
# Local development setup for logging.email

set -e

echo "=== logging.email Local Development Setup ==="

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3 required"; exit 1; }
command -v mysql >/dev/null 2>&1 || { echo "MySQL required"; exit 1; }
command -v redis-cli >/dev/null 2>&1 || { echo "Redis required"; exit 1; }

# Create virtual environments
echo "Creating virtual environments..."

cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

cd worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

cd policy-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# Setup database
echo "Setting up database..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS logging_email_dev;"
mysql -u root -p logging_email_dev < config/schema.sql

# Create .env files
echo "Creating .env files..."

cat > backend/.env << EOF
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=logging_email_dev
REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=email_processing_dev
JWT_SECRET=$(openssl rand -hex 32)
API_TOKEN_SALT=$(openssl rand -hex 32)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
DOMAIN=localhost
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8080
ATTACHMENT_STORAGE_PATH=./attachments
EOF

cat > worker/.env << EOF
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=logging_email_dev
REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=email_processing_dev
ATTACHMENT_STORAGE_PATH=./attachments
EOF

cat > policy-service/.env << EOF
API_TOKEN=dev_token_change_me
BACKEND_URL=http://localhost:8000
BIND_ADDRESS=127.0.0.1
BIND_PORT=10040
EOF

# Create attachment directory
mkdir -p attachments

echo ""
echo "✓ Setup complete!"
echo ""
echo "To run services:"
echo "  Backend:  cd backend && source venv/bin/activate && python main.py"
echo "  Worker:   cd worker && source venv/bin/activate && python worker.py"
echo "  Policy:   cd policy-service && source venv/bin/activate && python policy_daemon.py"
echo "  Frontend: cd frontend && python -m http.server 8080"
echo ""
echo "Generate API tokens:"
echo "  python config/generate_tokens.py"
