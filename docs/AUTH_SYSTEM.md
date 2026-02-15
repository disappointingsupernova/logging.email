# Session-Based Authentication System

## Overview
JWT + DB-backed refresh tokens + risk-based session management

## Architecture

### Token Types

**Access Token (JWT)**
- Lifetime: 15 minutes
- Stored: Client memory only
- Claims: `{sub: user_uuid, sid: session_id, iat, exp}`
- Stateless verification with session validation

**Refresh Token**
- Lifetime: 30 days
- Stored: HttpOnly cookie + DB (hashed)
- Rotates on every use
- Reuse detection triggers session revocation

### Database Models

**Session**
- Tracks device, browser, IP, ASN, country
- Risk score accumulates over time
- Revocable at any time

**RefreshToken**
- Hashed storage
- Linked to session
- Tracks replacement chain

**SecurityEvent**
- Audit trail for security events
- Login, logout, token reuse, risk events

## Risk Calculation

### Risk Thresholds
- `ROTATE_REFRESH_RISK = 40`: Force refresh token rotation
- `REAUTH_RISK = 70`: Require full re-authentication

### Risk Factors
| Event | Risk Score |
|-------|-----------|
| Device ID change | +40 |
| Client type change (web→mobile) | +30 |
| Browser family change | +20 |
| Browser version update | +5 |
| Geo jump (different country) | +25 |
| Same country, different ISP | +8 |
| Same ISP (WiFi ↔ 4G) | +2 |

## API Endpoints

### POST /auth/login
```json
{
  "email": "user@example.com",
  "password": "password",
  "device_id": "uuid",
  "client_id": "web"
}
```
Returns access token + sets refresh token cookie

### POST /auth/refresh
Uses refresh token from cookie, returns new access token + rotated refresh token

### POST /auth/logout
Revokes current session

### POST /auth/logout-all
Revokes all user sessions

### GET /auth/sessions
Lists active sessions with device info

## Request Headers

**Required for all authenticated requests:**
- `Authorization: Bearer <access_token>`

**Optional (improves risk detection):**
- `X-Device-ID`: Stable client-generated UUID
- `X-Client-ID`: web, ios, android, cli

## Security Features

✅ Short-lived access tokens (15 min)
✅ Refresh token rotation
✅ Reuse detection → session revocation
✅ Risk-based authentication
✅ WiFi ↔ 4G transitions allowed
✅ Browser auto-updates allowed
✅ Device change → re-auth required
✅ Redis cache with DB fallback
✅ Session revocation is immediate
✅ Security event audit trail

## Client Implementation

### Login Flow
```javascript
const response = await fetch('/auth/login', {
  method: 'POST',
  body: JSON.stringify({
    email, password,
    device_id: getDeviceId(), // localStorage UUID
    client_id: 'web'
  })
});
const { access_token } = await response.json();
// Store in memory only
```

### API Requests
```javascript
fetch('/api/messages', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'X-Device-ID': getDeviceId(),
    'X-Client-ID': 'web'
  }
});
```

### Token Refresh
```javascript
// On 401, refresh token
const response = await fetch('/auth/refresh', {
  method: 'POST',
  credentials: 'include' // Send cookie
});
const { access_token } = await response.json();
```

## MaxMind Integration (TODO)

Update `lib/services/session.py`:
```python
import geoip2.database

reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')

def get_geo_info(ip: str) -> dict:
    try:
        response = reader.city(ip)
        return {
            "asn": response.traits.autonomous_system_number,
            "country": response.country.iso_code
        }
    except:
        return {"asn": None, "country": None}
```

## Dependencies

Add to requirements.txt:
```
user-agents==2.2.0
geoip2==4.7.0  # Optional, for MaxMind
```
