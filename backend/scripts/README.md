# Backend Scripts

## create_admin.py

Creates a platform admin user.

**Usage:**
```bash
cd /path/to/backend
python scripts/create_admin.py
```

**Interactive prompts:**
- Admin email
- Password (hidden)
- Password confirmation

**Features:**
- Creates organization for admin
- Sets `is_platform_admin = True`
- Can promote existing users to admin

**Example:**
```bash
$ python scripts/create_admin.py
=== Create Platform Admin User ===

Admin email: admin@logging.email
Admin password: 
Confirm password: 

Hashing password...

✓ Platform admin user created successfully
  Email: admin@logging.email
  UUID: 550e8400-e29b-41d4-a716-446655440000
  Role: owner
  Platform Admin: True
  Organization: Platform Admin Organization
```
