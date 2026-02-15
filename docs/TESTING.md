# Testing Guide

## Unit Tests

### Backend Tests

Create `backend/test_auth.py`:
```python
import pytest
from auth import hash_password, verify_password, generate_api_token

def test_password_hashing():
    password = "test_password_123"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_api_token_generation():
    token, token_hash = generate_api_token()
    assert len(token) > 32
    assert len(token_hash) == 64  # SHA256 hex
```

Create `backend/test_policy.py`:
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_policy_check_invalid_token():
    response = client.post(
        "/policy/check",
        json={"recipient": "test@logging.email"},
        headers={"X-API-Token": "invalid"}
    )
    assert response.status_code == 401

def test_policy_check_unknown_recipient():
    # Requires valid token and database setup
    pass
```

### Worker Tests

Create `worker/test_worker.py`:
```python
import pytest
from worker import sanitise_html

def test_html_sanitisation():
    malicious = '<script>alert("xss")</script><p>Safe content</p>'
    sanitised = sanitise_html(malicious)
    assert '<script>' not in sanitised
    assert '<p>Safe content</p>' in sanitised

def test_html_sanitisation_removes_events():
    malicious = '<a href="#" onclick="alert()">Link</a>'
    sanitised = sanitise_html(malicious)
    assert 'onclick' not in sanitised
    assert '<a href="#">Link</a>' in sanitised
```

Run tests:
```bash
cd backend
source venv/bin/activate
pip install pytest
pytest
```

## Integration Tests

### Email Flow Test

```bash
#!/bin/bash
# test_email_flow.sh

# 1. Register customer
TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. Get email addresses
ADDRESSES=$(curl -s http://localhost:8000/addresses \
  -H "Authorization: Bearer $TOKEN")

echo "Addresses: $ADDRESSES"

# 3. Extract first address
EMAIL=$(echo $ADDRESSES | jq -r '.addresses[0].address')

echo "Email: $EMAIL"

# 4. Send test email
echo "Test message body" | mail -s "Test Subject" $EMAIL

# 5. Wait for processing
sleep 5

# 6. Check messages
MESSAGES=$(curl -s http://localhost:8000/messages \
  -H "Authorization: Bearer $TOKEN")

echo "Messages: $MESSAGES"
```

### Policy Service Test

```bash
#!/bin/bash
# test_policy.sh

# Test valid recipient
echo -e "request=smtpd_access_policy\nrecipient=valid@logging.email\n" \
  | nc 127.0.0.1 10040

# Expected: action=DUNNO

# Test invalid recipient
echo -e "request=smtpd_access_policy\nrecipient=invalid@logging.email\n" \
  | nc 127.0.0.1 10040

# Expected: action=REJECT Unknown recipient
```

### Stripe Webhook Test

```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8000/billing/webhook

# In another terminal, trigger test event
stripe trigger checkout.session.completed
```

## Load Tests

### Policy Service Load Test

Create `tests/load_test_policy.py`:
```python
import asyncio
import aiohttp
import time

async def check_policy(session, recipient):
    async with session.post(
        'http://localhost:8000/policy/check',
        json={'recipient': recipient},
        headers={'X-API-Token': 'YOUR_TOKEN'}
    ) as response:
        return await response.json()

async def main():
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(1000):
            tasks.append(check_policy(session, f'test{i}@logging.email'))
        results = await asyncio.gather(*tasks)
    
    duration = time.time() - start
    print(f"1000 requests in {duration:.2f}s")
    print(f"Rate: {1000/duration:.2f} req/s")

asyncio.run(main())
```

Run:
```bash
pip install aiohttp
python tests/load_test_policy.py
```

### SMTP Load Test

```bash
# Install smtp-source (postfix-utils)
smtp-source -c -l 1000 -m 100 -s 10 -f sender@test.com -t test@logging.email localhost:25
```

## Security Tests

### SQL Injection Test

```python
def test_sql_injection():
    # Try to inject SQL in recipient field
    malicious_recipient = "test@logging.email'; DROP TABLE customers; --"
    
    response = client.post(
        "/policy/check",
        json={"recipient": malicious_recipient},
        headers={"X-API-Token": "valid_token"}
    )
    
    # Should safely reject, not execute SQL
    assert response.status_code in [200, 400]
    
    # Verify table still exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        assert cursor.fetchone() is not None
```

### XSS Test

```python
def test_xss_sanitisation():
    xss_payloads = [
        '<script>alert("xss")</script>',
        '<img src=x onerror=alert("xss")>',
        '<iframe src="javascript:alert(\'xss\')">',
        '<body onload=alert("xss")>',
        '<svg/onload=alert("xss")>',
    ]
    
    for payload in xss_payloads:
        sanitised = sanitise_html(payload)
        assert '<script>' not in sanitised.lower()
        assert 'onerror' not in sanitised.lower()
        assert 'onload' not in sanitised.lower()
        assert 'javascript:' not in sanitised.lower()
```

### Authentication Test

```python
def test_jwt_expiry():
    # Create token with short expiry
    token = create_access_token({"sub": "test"}, expires_delta=timedelta(seconds=1))
    
    # Wait for expiry
    time.sleep(2)
    
    # Try to use expired token
    response = client.get(
        "/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 401
```

## Manual Testing Checklist

### Registration & Login
- [ ] Register with valid email
- [ ] Register with duplicate email (should fail)
- [ ] Register with invalid email format (should fail)
- [ ] Login with correct credentials
- [ ] Login with wrong password (should fail)
- [ ] Login with non-existent email (should fail)

### Email Addresses
- [ ] View default email address
- [ ] Create new email address (free tier)
- [ ] Try to create 4th address on free tier (should fail)
- [ ] Deactivate address
- [ ] Reactivate address
- [ ] Delete address

### Message Reception
- [ ] Send email to valid address
- [ ] Verify message appears in UI
- [ ] View message details
- [ ] Check text body rendering
- [ ] Check HTML body rendering (sanitised)
- [ ] Send email with attachment
- [ ] Verify attachment listed
- [ ] Send email to inactive address (should reject)
- [ ] Send email to non-existent address (should reject)

### Rate Limiting
- [ ] Send 100 emails rapidly (should accept)
- [ ] Send 101st email (should reject on free tier)
- [ ] Wait 1 hour
- [ ] Send email (should accept again)

### Billing
- [ ] Click upgrade button
- [ ] Complete Stripe checkout (test mode)
- [ ] Verify tier upgraded to paid
- [ ] Check increased limits
- [ ] Cancel subscription in Stripe portal
- [ ] Verify downgrade to free tier

### Security
- [ ] Try to access another customer's messages (should fail)
- [ ] Try to use expired JWT (should fail)
- [ ] Try to use invalid API token (should fail)
- [ ] Send email with XSS payload
- [ ] Verify HTML sanitised in UI
- [ ] Send email with malicious attachment name
- [ ] Verify safe storage

### Retention
- [ ] Create message
- [ ] Wait 8 days (free tier)
- [ ] Run cleanup cron
- [ ] Verify message deleted
- [ ] Verify attachment deleted from storage

## Performance Benchmarks

### Target Metrics
- Policy check: < 50ms (p95)
- Email ingestion: < 100ms (p95)
- Message processing: < 5s (p95)
- API response: < 200ms (p95)
- UI load: < 2s (p95)

### Monitoring
```bash
# Policy service latency
time echo -e "request=smtpd_access_policy\nrecipient=test@logging.email\n" | nc 127.0.0.1 10040

# API latency
time curl -s http://localhost:8000/messages -H "Authorization: Bearer $TOKEN"

# Queue depth
redis-cli LLEN email_processing

# Database connections
mysql -e "SHOW PROCESSLIST"
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: logging_email_test
        ports:
          - 3306:3306
      
      redis:
        image: redis:6
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run tests
        run: |
          cd backend
          pytest
        env:
          DB_HOST: 127.0.0.1
          DB_PASSWORD: root
          DB_NAME: logging_email_test
```

## Deployment Testing

### Pre-Deployment
- [ ] All tests passing
- [ ] Database migrations applied
- [ ] Environment variables set
- [ ] TLS certificates valid
- [ ] DNS records correct
- [ ] Firewall rules applied

### Post-Deployment
- [ ] Health check endpoint responding
- [ ] Policy service accepting connections
- [ ] Worker processing queue
- [ ] Frontend loading
- [ ] Test email flow end-to-end
- [ ] Stripe webhooks receiving events
- [ ] Monitoring alerts configured

### Rollback Plan
1. Stop new services
2. Restore database backup
3. Start old services
4. Verify functionality
5. Investigate failure
