# Business Logic & Tier System

## Tier Comparison

| Feature | Free | Paid |
|---------|------|------|
| Email addresses | 3 | 50 |
| Retention | 7 days | 90 days |
| Rate limit | 100/hour | 1000/hour |
| Ads | Yes | No |
| Priority support | No | Yes |
| Price | £0/month | £9/month |

## Customer Lifecycle

### Registration
1. Customer registers with email + password
2. Account created with `tier = 'free'`
3. Default email address created: `{uuid}@logging.email`
4. JWT token issued
5. Customer can immediately receive emails

### Free Tier Usage
- Customer can create up to 3 email addresses
- Messages retained for 7 days
- Rate limited to 100 emails/hour per address
- Ads displayed in web UI
- Automatic cleanup after 7 days

### Upgrade to Paid
1. Customer clicks "Upgrade" in UI
2. Backend creates Stripe Checkout session
3. Customer redirected to Stripe
4. Customer enters payment details
5. Stripe webhook fires `checkout.session.completed`
6. Backend updates `tier = 'paid'`
7. Subscription record created
8. Customer redirected back to UI
9. Limits immediately increased

### Paid Tier Usage
- Customer can create up to 50 email addresses
- Messages retained for 90 days
- Rate limited to 1000 emails/hour per address
- No ads in UI
- Priority support

### Subscription Management
- Stripe handles recurring billing
- Webhook updates subscription status
- If payment fails: `status = 'past_due'`
- If cancelled: `status = 'cancelled'`, `tier = 'free'`
- Downgrade to free tier limits applied immediately

### Cancellation
1. Customer cancels in Stripe portal
2. Webhook fires `customer.subscription.deleted`
3. Backend downgrades to free tier
4. Excess addresses remain but inactive
5. Messages beyond 7 days deleted on next cleanup

### Account Deletion
1. Customer requests deletion
2. All email addresses deleted (cascade)
3. All messages deleted (cascade)
4. All attachments deleted from storage
5. Subscription cancelled in Stripe
6. Customer record deleted

## Email Address Management

### Creation
- Free tier: Max 3 addresses
- Paid tier: Max 50 addresses
- Format: `{anything}@logging.email` (customer chooses)
- Must be unique across platform
- Automatically active on creation

### Deactivation
- Customer can deactivate addresses
- Deactivated addresses reject mail at RCPT stage
- Can be reactivated later
- Does not count towards limit when inactive

### Deletion
- Cascade deletes all messages
- Cascade deletes all attachments
- Cannot be undone
- Frees up slot in limit

## Message Processing

### Inbound Flow
1. Email arrives at Postfix MX
2. Postfix queries policy service at RCPT TO
3. Policy service checks:
   - Address exists
   - Address is active
   - Rate limit not exceeded
4. If OK: Postfix accepts (250 OK)
5. If REJECT: Postfix rejects (550 error)
6. Accepted email forwarded to backend
7. Backend creates message record (unprocessed)
8. Backend enqueues job in Redis
9. Worker picks up job
10. Worker parses email safely
11. Worker sanitises HTML
12. Worker stores attachments
13. Worker updates message (processed)
14. Customer sees message in UI

### Rate Limiting
- Enforced at policy check stage
- Counted per address, not per customer
- Rolling 1-hour window
- Exceeding limit = REJECT at SMTP level
- Prevents queue flooding

### Retention
- Enforced by daily cron job
- Deletes messages older than tier limit
- Cascade deletes attachments
- Frees up storage space

## Revenue Model

### Pricing
- Free tier: £0/month (ad-supported)
- Paid tier: £9/month (billed monthly)
- Annual option: £90/year (2 months free)

### Stripe Integration
- Stripe Checkout for upgrades
- Stripe Customer Portal for management
- Webhooks for status updates
- Automatic retry on failed payments
- Dunning emails via Stripe

### Ad Revenue (Free Tier)
- Display ads in web UI
- Google AdSense or similar
- Non-intrusive placement
- No ads in emails (never modify content)

## Operational Costs

### Per Customer (Free)
- Storage: ~10MB (7 days × ~100 emails × ~15KB avg)
- Database: Minimal
- Bandwidth: ~1MB/day
- Compute: Negligible
- **Total: ~£0.01/month**

### Per Customer (Paid)
- Storage: ~130MB (90 days × ~1000 emails × ~15KB avg)
- Database: Moderate
- Bandwidth: ~10MB/day
- Compute: Low
- **Total: ~£0.50/month**

### Break-Even
- Paid tier profitable at £9/month
- Free tier profitable with ads (£0.50 CPM)
- Target: 10,000 free users, 1,000 paid users
- Revenue: £9,000/month
- Costs: ~£1,500/month (infrastructure + support)
- Profit: ~£7,500/month

## Growth Strategy

### Acquisition
- Developer-focused marketing
- Integration with notify.work
- API documentation and examples
- Free tier as lead magnet

### Retention
- Reliable service (99.9% uptime)
- Fast email delivery
- Clean, simple UI
- Responsive support

### Expansion
- Custom domains (£19/month)
- Webhooks (included in paid)
- API access (included in paid)
- Team accounts (£29/month for 5 users)

## Future Features

### Phase 2
- Webhooks for new messages
- Email forwarding rules
- Search and filters
- Mobile app

### Phase 3
- Custom domains with DKIM
- Team collaboration
- Shared inboxes
- Advanced analytics

### Phase 4
- Integration with ownyour.email
- White-label offering
- Enterprise tier
- SLA guarantees

## Compliance

### GDPR
- Data minimisation
- Right to access (export)
- Right to deletion (account deletion)
- Data retention limits
- Privacy policy

### Terms of Service
- No spam sending (inbound only)
- No illegal content
- No abuse of service
- Suspension for violations
- Termination clause

### Acceptable Use
- Logging and testing only
- No production email
- No sensitive data (PII, PHI, PCI)
- No forwarding to external addresses
- No automated scraping
