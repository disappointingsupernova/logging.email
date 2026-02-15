#!/usr/bin/env python3
"""
Create platform admin user for logging.email.
Run this on the server to create a platform admin account.
"""
import sys
import uuid
from getpass import getpass
from lib.utils.auth import hash_password
from lib.database import SessionLocal
from models.models import User, Organization

def create_admin():
    print("=== Create Platform Admin User ===\n")
    
    email = input("Admin email: ").strip()
    if not email:
        print("ERROR: Email is required")
        sys.exit(1)
    
    password = getpass("Admin password: ")
    if not password:
        print("ERROR: Password is required")
        sys.exit(1)
    
    password_confirm = getpass("Confirm password: ")
    if password != password_confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)
    
    print("\nHashing password...")
    password_hash = hash_password(password)
    
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"ERROR: Email {email} already exists")
            promote = input("Promote existing user to platform admin? (y/n): ").strip().lower()
            if promote == 'y':
                existing.is_platform_admin = True
                db.commit()
                print(f"✓ User {email} promoted to platform admin")
            sys.exit(0)
        
        # Create organization for admin
        org = Organization(
            uuid=str(uuid.uuid4()),
            name="Platform Admin Organization",
            tier='paid'
        )
        db.add(org)
        db.flush()
        
        # Create admin user
        admin = User(
            organization_id=org.id,
            uuid=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            role='owner',
            is_platform_admin=True
        )
        db.add(admin)
        db.commit()
        
        print(f"\n✓ Platform admin user created successfully")
        print(f"  Email: {email}")
        print(f"  UUID: {admin.uuid}")
        print(f"  Role: owner")
        print(f"  Platform Admin: True")
        print(f"  Organization: {org.name}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
