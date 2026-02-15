# Security Architecture

## Threat Model

### Threats

1. **Malicious email content** - XSS, code execution, phishing
2. **SMTP abuse** - Spam relay, DDoS
3. **Data breaches** - Unauthorised access to messages
4. **Service disruption** - Resource exhaustion
5. **Credential theft** - Customer account compromise

### Mitigations

## Email Content Security

### Never Execute Content

- All email parsed with Python's `email` module only
- No `eval()`, `exec()`, or dynamic imports
- No shell execution of filenames or content
- Attachments stored as binary blobs, never opened

### HTML Sanitisation

- `bleach` library with strict allowlist
- Only safe tags: `p`, `br`, `strong`, `em`, `u`, `a`, `ul`, `ol`, `li`, `blockquote`, `pre`, `code`
- Only safe attributes: `href` and `title` on `<a>` tags
- All JavaScript stripped
- All event handlers removed
- All `<script>`, `<iframe>`, `<object>`, `<embed>` removed

### Attachment Handling

- Stored outside web root
- Filename sanitised (hashed prefix)
- MIME type detected and stored
- Never served with executable MIME types
- Optional: ClamAV scanning before storage

## SMTP Security

### Postfix Hardening

- Inbound only, no relay
- No local delivery
- HELO required
- Strict RFC821 envelopes
- Rate limiting per client
- Connection limits
- TLS opportunistic inbound, mandatory outbound

### Policy Service

- Runs on localhost only (127.0.0.1)
- No direct internet exposure
- No database access
- Single API token for backend auth
- Fails closed on any error
- Timeout protection (5s)
- TLS verification mandatory

### Recipient Validation

- Checked at RCPT TO stage (before DATA)
- No catch-all addresses
- Active/inactive status enforced
- Rate limits per tier enforced
- Invalid recipients rejected immediately

## API Security

### Authentication

- JWT tokens for customers (24h expiry)
- API tokens for services (policy, worker)
- Tokens hashed with salt before storage
- Constant-time comparison
- Argon2 for password hashing (memory-hard, resistant to GPU attacks)

### Audit Logging

- All user actions logged to database
- IP address and user agent captured
- Failed login attempts tracked
- Audit log retained indefinitely
- Customer can view own audit log
- See [docs/AUDIT.md](AUDIT.md) for details

### Authorisation

- Customer can only access own messages
- Policy service scope limited to recipient checks
- Worker scope limited to ingestion
- Admin scope for management operations

### Transport Security

- TLS 1.2+ only
- Strong cipher suites only
- Certificate verification mandatory
- HSTS headers
- No mixed content

### Input Validation

- All inputs validated with Pydantic
- Email addresses validated
- UUIDs treated as opaque strings
- SQL parameterised queries only
- No string concatenation in queries

## Data Protection

### At Rest

- Database encrypted (MySQL encryption at rest)
- Attachments on encrypted filesystem
- Backups encrypted
- Secrets in environment files (600 permissions)

### In Transit

- TLS for all external communication
- TLS for backend ↔ policy service
- TLS for backend ↔ Stripe

### Retention

- Free tier: 7 days
- Paid tier: 90 days
- Automatic deletion via cron
- Cascade deletes for attachments

### Privacy

- No email content analysis
- No tracking pixels
- No third-party analytics
- Minimal logging (no message bodies)

## Infrastructure Security

### Separation of Concerns

- MX hosts: Postfix + Policy service only
- Backend hosts: API + Workers + Database
- Frontend hosts: Static files + nginx

### Least Privilege

- Separate system users per service
- No root execution
- Read-only filesystems where possible
- Minimal file permissions

### Network Segmentation

- MX hosts in DMZ
- Backend in private network
- Database not internet-facing
- Firewall rules between zones

### Service Hardening

- systemd security features:
  - `NoNewPrivileges=true`
  - `PrivateTmp=true`
  - `ProtectSystem=strict`
  - `ProtectHome=true`
  - `ReadOnlyPaths` where applicable

## Operational Security

### Secrets Management

- Environment files, not code
- 600 permissions on .env files
- Separate secrets per environment
- Rotate API tokens regularly
- Stripe keys in environment only

### Logging

- No sensitive data in logs
- No passwords or tokens logged
- Structured logging for SIEM
- Log retention policy
- Audit trail for admin actions

### Monitoring

- Failed login attempts
- Policy service rejections
- Rate limit violations
- Queue depth
- Disk usage (attachments)
- Database connections

### Incident Response

1. Isolate affected systems
2. Review logs for IOCs
3. Rotate compromised credentials
4. Notify affected customers
5. Document and remediate

## Compliance

### GDPR

- Customer data minimisation
- Right to deletion (account deletion)
- Data export capability
- Privacy policy
- Cookie consent (if tracking added)

### PCI DSS

- No card data stored
- Stripe handles all payment data
- PCI compliance via Stripe

## Security Testing

### Regular Activities

- Dependency updates (Dependabot)
- Vulnerability scanning (Snyk, Trivy)
- Penetration testing (annual)
- Code review for changes
- Security headers testing

### Pre-Deployment Checklist

- [ ] All secrets rotated
- [ ] TLS certificates valid
- [ ] Firewall rules applied
- [ ] Service users created
- [ ] File permissions correct
- [ ] Backups configured
- [ ] Monitoring enabled
- [ ] Rate limits tested
- [ ] Policy service fails closed
- [ ] HTML sanitisation verified

## Known Limitations

1. **No SPF/DKIM/DMARC validation** - Accept all mail (by design)
2. **No virus scanning** - Optional, not implemented
3. **No spam filtering** - Logging service, not filtering
4. **Attachment size limits** - 25MB per message
5. **No email forwarding** - One-way inbound only

## Future Enhancements

- Two-factor authentication
- API rate limiting (per customer)
- Webhook delivery for new messages
- S3 storage for attachments
- CloudFlare Email Routing integration
- Custom domain support (DKIM signing)
