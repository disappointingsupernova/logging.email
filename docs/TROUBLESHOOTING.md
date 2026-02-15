# Troubleshooting Guide

Common issues and solutions for logging.email.

## Installation Issues

### Database Connection Failed

**Symptom**: `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")`

**Solutions**:
1. Check MySQL is running: `sudo systemctl status mysql`
2. Verify credentials in `.env` file
3. Test connection: `mysql -u logging_email -p -h localhost`
4. Check firewall: `sudo ufw status`
5. Verify MySQL listening: `sudo netstat -tlnp | grep 3306`

### Redis Connection Failed

**Symptom**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solutions**:
1. Check Redis is running: `sudo systemctl status redis`
2. Verify Redis URL in `.env` file
3. Test connection: `redis-cli ping` (should return PONG)
4. Check Redis config: `/etc/redis/redis.conf`
5. Ensure Redis listening on correct interface

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'fastapi'`

**Solutions**:
1. Activate virtual environment: `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Check Python version: `python --version` (need 3.10+)
4. Recreate venv if corrupted: `rm -rf venv && python3 -m venv venv`

## SMTP Issues

### Postfix Not Accepting Mail

**Symptom**: `Connection refused` when sending to MX

**Solutions**:
1. Check Postfix running: `sudo systemctl status postfix`
2. Check port 25 open: `sudo netstat -tlnp | grep :25`
3. Test locally: `telnet localhost 25`
4. Check firewall: `sudo ufw allow 25/tcp`
5. Review logs: `sudo tail -f /var/log/mail.log`

### All Mail Rejected

**Symptom**: `550 5.1.1 Recipient address rejected`

**Solutions**:
1. Check policy service running: `sudo systemctl status policy-service`
2. Test policy service: `echo -e "request=smtpd_access_policy\nrecipient=test@logging.email\n" | nc 127.0.0.1 10040`
3. Verify API token in `/etc/logging-email/policy.env`
4. Check backend API accessible: `curl https://api.logging.email/health`
5. Review policy logs: `sudo journalctl -u policy-service -f`

### Policy Service Not Responding

**Symptom**: Postfix logs show policy timeout

**Solutions**:
1. Check policy service logs: `sudo journalctl -u policy-service -n 50`
2. Verify backend URL in policy.env
3. Test backend connectivity: `curl -H "X-API-Token: TOKEN" https://api.logging.email/policy/check -d '{"recipient":"test@logging.email"}'`
4. Check TLS certificates valid
5. Increase timeout in Postfix: `smtpd_policy_service_timeout = 10s`

## Email Processing Issues

### Messages Not Appearing in UI

**Symptom**: Email accepted but not visible in frontend

**Solutions**:
1. Check worker running: `sudo systemctl status worker`
2. Check queue depth: `redis-cli LLEN email_processing`
3. Check worker logs: `sudo journalctl -u worker -f`
4. Verify message in database: `mysql -u logging_email -p -e "SELECT * FROM messages ORDER BY received_at DESC LIMIT 5" logging_email`
5. Check `is_processed` flag: Should be TRUE

### Worker Crashing

**Symptom**: Worker service keeps restarting

**Solutions**:
1. Check logs: `sudo journalctl -u worker -n 100`
2. Check disk space: `df -h`
3. Check attachment directory writable: `ls -la /var/lib/logging-email/attachments`
4. Verify database connection
5. Check for malformed emails in queue

### Queue Growing Indefinitely

**Symptom**: Redis queue depth increasing, not processing

**Solutions**:
1. Check worker running and not erroring
2. Scale workers: Run multiple worker processes
3. Check for stuck jobs: `redis-cli LRANGE email_processing 0 10`
4. Clear queue if needed: `redis-cli DEL email_processing`
5. Check database not full: `df -h`

## API Issues

### 401 Unauthorized

**Symptom**: API returns 401 for authenticated requests

**Solutions**:
1. Check JWT token not expired (24h lifetime)
2. Verify Authorization header format: `Bearer <token>`
3. Check JWT_SECRET matches between requests
4. Re-login to get fresh token
5. Check system clock synchronized (NTP)

### 500 Internal Server Error

**Symptom**: API returns 500 for valid requests

**Solutions**:
1. Check backend logs: `sudo journalctl -u backend -f`
2. Verify database connection
3. Check disk space: `df -h`
4. Review error traceback in logs
5. Check environment variables set correctly

### CORS Errors

**Symptom**: Browser console shows CORS errors

**Solutions**:
1. Verify FRONTEND_URL in backend .env matches actual frontend URL
2. Check CORS middleware configured in main.py
3. Use same protocol (http/https) for frontend and backend
4. Check browser not blocking mixed content
5. Test API directly with curl (bypasses CORS)

## Billing Issues

### Stripe Checkout Not Working

**Symptom**: Clicking upgrade does nothing or errors

**Solutions**:
1. Check Stripe API keys in backend .env
2. Verify Stripe account active
3. Check price ID exists: `stripe prices list`
4. Review backend logs for Stripe errors
5. Test with Stripe test mode first

### Webhooks Not Received

**Symptom**: Subscription created but tier not upgraded

**Solutions**:
1. Check webhook endpoint accessible: `curl https://api.logging.email/billing/webhook`
2. Verify webhook secret in backend .env
3. Check Stripe webhook logs in dashboard
4. Test with Stripe CLI: `stripe listen --forward-to localhost:8000/billing/webhook`
5. Ensure webhook endpoint not behind auth

### Tier Not Upgrading

**Symptom**: Payment successful but still on free tier

**Solutions**:
1. Check webhook received: Review backend logs
2. Verify subscription record created: `SELECT * FROM subscriptions`
3. Check customer tier updated: `SELECT tier FROM customers WHERE email = 'user@example.com'`
4. Manually update if needed: `UPDATE customers SET tier = 'paid' WHERE email = 'user@example.com'`
5. Check Stripe webhook event type: Should be `checkout.session.completed`

## Frontend Issues

### Login Not Working

**Symptom**: Login button does nothing or shows error

**Solutions**:
1. Check browser console for errors
2. Verify backend API URL in frontend code
3. Test API directly: `curl -X POST http://localhost:8000/auth/login -d '{"email":"test@example.com","password":"test123"}'`
4. Check CORS configuration
5. Verify credentials correct in database

### Messages Not Loading

**Symptom**: Dashboard shows but no messages

**Solutions**:
1. Check browser console for errors
2. Verify JWT token stored: `localStorage.getItem('token')`
3. Test API: `curl -H "Authorization: Bearer TOKEN" http://localhost:8000/messages`
4. Check messages exist in database
5. Verify `is_processed = TRUE` for messages

### HTML Not Rendering

**Symptom**: Message body shows raw HTML or nothing

**Solutions**:
1. Check `sanitised_html` field populated in database
2. Verify worker processed message: `is_processed = TRUE`
3. Check worker logs for sanitisation errors
4. Test sanitisation: `python -c "from worker import sanitise_html; print(sanitise_html('<p>test</p>'))"`
5. Ensure bleach library installed

## Performance Issues

### Slow Policy Checks

**Symptom**: SMTP sessions slow, timeouts

**Solutions**:
1. Check database query performance: `EXPLAIN SELECT ...`
2. Add indexes if missing: See schema.sql
3. Optimize backend API response time
4. Increase policy service timeout
5. Scale backend horizontally

### High Memory Usage

**Symptom**: Services using excessive RAM

**Solutions**:
1. Check for memory leaks: Monitor over time
2. Restart services periodically
3. Limit worker concurrency
4. Optimize database queries
5. Add swap space if needed

### Disk Space Full

**Symptom**: Services failing, disk at 100%

**Solutions**:
1. Check attachment storage: `du -sh /var/lib/logging-email/attachments`
2. Run retention cleanup: See DEPLOYMENT.md
3. Check database size: `SELECT table_schema, SUM(data_length + index_length) / 1024 / 1024 AS "Size (MB)" FROM information_schema.tables GROUP BY table_schema`
4. Clean old logs: `sudo journalctl --vacuum-time=7d`
5. Increase disk size or add volume

## Security Issues

### Suspected Breach

**Actions**:
1. Isolate affected systems immediately
2. Review logs for suspicious activity
3. Rotate all API tokens: `python config/generate_tokens.py`
4. Rotate JWT secret in backend .env
5. Force password reset for all customers
6. Review database for unauthorized access
7. Check for modified files: `sudo debsums -c`
8. Document incident and timeline

### XSS Detected

**Actions**:
1. Verify HTML sanitisation working: Test with known XSS payloads
2. Check bleach version up to date: `pip list | grep bleach`
3. Review sanitisation allowlist in worker.py
4. Test all message rendering paths
5. Update bleach if vulnerability found

### Rate Limit Bypass

**Actions**:
1. Check rate limit logic in policy.py
2. Verify database queries correct
3. Add additional rate limiting at nginx level
4. Block abusive IPs in firewall
5. Review logs for patterns

## Monitoring & Debugging

### Enable Debug Logging

Backend:
```python
# In main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Worker:
```python
# In worker.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Useful Commands

```bash
# Check all services
sudo systemctl status backend worker policy-service postfix redis mysql

# View logs
sudo journalctl -u backend -f
sudo journalctl -u worker -f
sudo journalctl -u policy-service -f
sudo tail -f /var/log/mail.log

# Check queue
redis-cli LLEN email_processing

# Check database
mysql -u logging_email -p logging_email
SELECT COUNT(*) FROM messages;
SELECT COUNT(*) FROM messages WHERE is_processed = FALSE;

# Check disk
df -h
du -sh /var/lib/logging-email/attachments

# Check network
sudo netstat -tlnp
sudo ss -tlnp

# Check processes
ps aux | grep python
ps aux | grep postfix

# Test connectivity
curl https://api.logging.email/health
redis-cli ping
mysql -u logging_email -p -e "SELECT 1"
```

## Getting Help

If you can't resolve the issue:

1. Check [docs/](docs/) for relevant documentation
2. Search [GitHub Issues](https://github.com/yourusername/logging.email/issues)
3. Create new issue with:
   - Symptom description
   - Steps to reproduce
   - Relevant logs
   - Environment details (OS, versions)
4. For security issues: Email security@logging.email (do not open public issue)

## Preventive Maintenance

### Daily
- Monitor disk space
- Check service status
- Review error logs

### Weekly
- Review rate limit violations
- Check queue depth trends
- Update dependencies

### Monthly
- Rotate logs
- Review security alerts
- Test backups
- Update system packages

### Quarterly
- Security audit
- Performance review
- Capacity planning
- Disaster recovery test
