from lib.database import get_db
from typing import Optional
import json

def log_audit(
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
    admin_id: Optional[int] = None
):
    """Log audit event to database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (user_id, admin_id, action, resource_type, resource_id, ip_address, user_agent, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            admin_id,
            action,
            resource_type,
            resource_id,
            ip_address,
            user_agent,
            json.dumps(details) if details else None
        ))
