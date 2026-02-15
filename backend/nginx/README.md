# Nginx Configuration for logging.email API

## Overview

Nginx reverse proxy configuration for `api.logging.email` with:
- Cloudflare real IP restoration
- Let's Encrypt wildcard SSL certificate
- Rate limiting
- Security headers
- Internal endpoint protection

## Installation

### 1. Copy Configuration

```bash
# Copy main config
sudo cp api.logging.email.conf /etc/nginx/sites-available/

# Copy snippets
sudo mkdir -p /etc/nginx/snippets
sudo cp snippets/*.conf /etc/nginx/snippets/

# Enable site
sudo ln -s /etc/nginx/sites-available/api.logging.email.conf /etc/nginx/sites-enabled/
```

### 2. Generate DH Parameters

```bash
sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048
```

### 3. Test Configuration

```bash
sudo nginx -t
```

### 4. Reload Nginx

```bash
sudo systemctl reload nginx
```

## SSL Certificate Setup

### Let's Encrypt Wildcard Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get wildcard certificate (requires DNS challenge)
sudo certbot certonly --manual --preferred-challenges dns \
  -d logging.email -d *.logging.email

# Certificate will be at:
# /etc/letsencrypt/live/logging.email/fullchain.pem
# /etc/letsencrypt/live/logging.email/privkey.pem
```

### Auto-renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up cron/systemd timer
```

## Cloudflare Configuration

### DNS Settings

```
Type: A
Name: api
Content: YOUR_SERVER_IP
Proxy: Enabled (orange cloud)
```

### SSL/TLS Settings

- SSL/TLS encryption mode: **Full (strict)**
- Always Use HTTPS: **On**
- Minimum TLS Version: **TLS 1.2**

### Firewall Rules (Optional)

Allow only Cloudflare IPs to port 443:
```bash
# UFW example
sudo ufw allow from 173.245.48.0/20 to any port 443
sudo ufw allow from 103.21.244.0/22 to any port 443
# ... add all Cloudflare ranges
```

## Rate Limiting

Configured zones:
- **api_limit**: 100 requests/minute (general API)
- **auth_limit**: 10 requests/minute (auth endpoints)

Adjust in main config:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
```

## Protected Endpoints

### Internal Only (localhost)

- `/policy/check` - SMTP policy service
- `/ingest` - Email ingestion

These endpoints are restricted to `127.0.0.1` and should only be accessed by local services.

### No Rate Limit

- `/health` - Health checks
- `/billing/webhook` - Stripe webhooks

## Monitoring

### Access Logs

```bash
tail -f /var/log/nginx/api.logging.email.access.log
```

### Error Logs

```bash
tail -f /var/log/nginx/api.logging.email.error.log
```

### Real-time Connections

```bash
watch -n 1 'netstat -an | grep :443 | wc -l'
```

## Performance Tuning

### Worker Connections

Edit `/etc/nginx/nginx.conf`:
```nginx
events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}
```

### Keepalive

```nginx
upstream backend_api {
    server 127.0.0.1:8000;
    keepalive 64;  # Increase for high traffic
}
```

### Buffer Sizes

```nginx
client_body_buffer_size 128k;
client_max_body_size 50M;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;
```

## Troubleshooting

### 502 Bad Gateway

```bash
# Check backend is running
curl http://127.0.0.1:8000/health

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Real IP Not Working

```bash
# Verify Cloudflare IPs are current
curl https://www.cloudflare.com/ips-v4
curl https://www.cloudflare.com/ips-v6

# Update cloudflare-realip.conf if needed
```

### Rate Limit Issues

```bash
# Check rate limit zone
sudo grep -i "limiting requests" /var/log/nginx/error.log

# Adjust burst parameter
limit_req zone=api_limit burst=50 nodelay;
```

## Security Checklist

- [ ] SSL certificate installed and valid
- [ ] Cloudflare proxy enabled (orange cloud)
- [ ] Real IP restoration configured
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] Internal endpoints protected
- [ ] Firewall rules configured
- [ ] Logs monitored
- [ ] Auto-renewal tested

## Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)
- [Let's Encrypt](https://letsencrypt.org/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
