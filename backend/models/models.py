from sqlalchemy import Column, BigInteger, String, Enum, Boolean, Integer, Text, TIMESTAMP, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from models import Base

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    tier = Column(String(63), nullable=False, default='free', index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_org_tier_created', 'tier', 'created_at'),
    )

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('owner', 'admin', 'member'), nullable=False, default='owner', index=True)
    is_platform_admin = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_user_org_role', 'organization_id', 'role'),
        Index('idx_user_org_created', 'organization_id', 'created_at'),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum('active', 'cancelled', 'past_due', 'unpaid'), nullable=False, index=True)
    current_period_end = Column(TIMESTAMP, nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_sub_org_status', 'organization_id', 'status'),
        Index('idx_sub_status_period', 'status', 'current_period_end'),
    )

class EmailAddress(Base):
    __tablename__ = "email_addresses"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_addr_org_active', 'organization_id', 'is_active'),
        Index('idx_addr_active_created', 'is_active', 'created_at'),
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email_address_id = Column(BigInteger, ForeignKey('email_addresses.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = Column(String(255), nullable=True, index=True)
    from_address = Column(String(255), nullable=False, index=True)
    subject = Column(Text, nullable=True)
    received_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    size_bytes = Column(Integer, nullable=False)
    has_attachments = Column(Boolean, nullable=False, default=False, index=True)
    is_processed = Column(Boolean, nullable=False, default=False, index=True)
    
    __table_args__ = (
        Index('idx_msg_addr_received', 'email_address_id', 'received_at'),
        Index('idx_msg_addr_processed', 'email_address_id', 'is_processed', 'received_at'),
        Index('idx_msg_processed_received', 'is_processed', 'received_at'),
        Index('idx_msg_from_received', 'from_address', 'received_at'),
    )

class Attachment(Base):
    __tablename__ = "attachments"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    mongodb_id = Column(String(24), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(127), nullable=False, index=True)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_attach_msg_created', 'message_id', 'created_at'),
    )

class ApiToken(Base):
    __tablename__ = "api_tokens"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False)
    scope = Column(Enum('policy', 'worker', 'admin'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    last_used_at = Column(TIMESTAMP, nullable=True, index=True)
    
    __table_args__ = (
        Index('idx_token_scope_active', 'scope', 'is_active'),
    )

class TierLimit(Base):
    __tablename__ = "tier_limits"
    
    tier = Column(String(63), primary_key=True)
    max_addresses = Column(Integer, nullable=False)
    retention_days = Column(Integer, nullable=False)
    rate_limit_per_hour = Column(Integer, nullable=False)
    max_storage_mb = Column(Integer, nullable=False, default=100)
    api_enabled = Column(Boolean, nullable=False, default=False)
    webhook_enabled = Column(Boolean, nullable=False, default=False)
    priority_support = Column(Boolean, nullable=False, default=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    admin_id = Column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = Column(String(127), nullable=False, index=True)
    resource_type = Column(String(63), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_audit_user_created', 'user_id', 'created_at'),
        Index('idx_audit_action_created', 'action', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id', 'created_at'),
        Index('idx_audit_ip_created', 'ip_address', 'created_at'),
    )

class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    period_start = Column(TIMESTAMP, nullable=False, index=True)
    period_end = Column(TIMESTAMP, nullable=False)
    emails_received = Column(Integer, nullable=False, default=0)
    storage_used_mb = Column(Integer, nullable=False, default=0)
    api_calls = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_usage_org_period', 'organization_id', 'period_start', unique=True),
    )

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    last_seen_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    revoked_at = Column(TIMESTAMP, nullable=True, index=True)
    
    device_id = Column(String(36), nullable=True, index=True)
    client_id = Column(String(63), nullable=True, index=True)
    user_agent_hash = Column(String(64), nullable=True)
    os_family = Column(String(63), nullable=True)
    browser_family = Column(String(63), nullable=True)
    
    last_ip = Column(String(45), nullable=True, index=True)
    last_asn = Column(Integer, nullable=True)
    last_country = Column(String(2), nullable=True, index=True)
    
    risk_score = Column(Integer, nullable=False, default=0, index=True)
    
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'revoked_at', 'expires_at'),
        Index('idx_session_active_lastseen', 'revoked_at', 'last_seen_at'),
        Index('idx_session_device', 'device_id', 'user_id'),
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    revoked_at = Column(TIMESTAMP, nullable=True, index=True)
    replaced_by = Column(String(36), nullable=True, index=True)
    
    __table_args__ = (
        Index('idx_refresh_session_active', 'session_id', 'revoked_at'),
        Index('idx_refresh_expires', 'expires_at', 'revoked_at'),
    )

class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(63), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_secevent_user_type_created', 'user_id', 'event_type', 'created_at'),
        Index('idx_secevent_session_created', 'session_id', 'created_at'),
        Index('idx_secevent_type_created', 'event_type', 'created_at'),
    )

class OutboundEmail(Base):
    __tablename__ = "outbound_emails"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    recipient = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    email_type = Column(String(63), nullable=False, index=True)
    template_id = Column(BigInteger, ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True, index=True)
    template_data = Column(JSON, nullable=True)
    
    status = Column(Enum('pending', 'sent', 'failed', 'expired'), nullable=False, default='pending', index=True)
    smtp_response = Column(Text, nullable=True)
    smtp_code = Column(Integer, nullable=True)
    
    attempts = Column(Integer, nullable=False, default=0, index=True)
    max_attempts = Column(Integer, nullable=False, default=5)
    next_retry_at = Column(TIMESTAMP, nullable=True, index=True)
    last_attempt_at = Column(TIMESTAMP, nullable=True, index=True)
    sent_at = Column(TIMESTAMP, nullable=True, index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    organization_id = Column(BigInteger, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True)
    
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_email_status_retry', 'status', 'next_retry_at'),
        Index('idx_email_status_expires', 'status', 'expires_at'),
        Index('idx_email_type_status_created', 'email_type', 'status', 'created_at'),
        Index('idx_email_recipient_created', 'recipient', 'created_at'),
        Index('idx_email_user_created', 'user_id', 'created_at'),
        Index('idx_email_org_created', 'organization_id', 'created_at'),
    )

class ServiceHealth(Base):
    __tablename__ = "service_health"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_name = Column(String(63), nullable=False, index=True)
    status = Column(Enum('healthy', 'degraded', 'down'), nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_health_service_checked', 'service_name', 'checked_at'),
        Index('idx_health_status_checked', 'status', 'checked_at'),
    )

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(63), unique=True, nullable=False, index=True)
    email_type = Column(String(63), nullable=True, index=True)
    subject_template = Column(String(255), nullable=False)
    body_text_template = Column(Text, nullable=True)
    body_html_template = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_template_type_active', 'email_type', 'is_active'),
    )
