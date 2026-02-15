from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database (MySQL - Structured Data)
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "logging_email"
    db_password: str
    db_name: str = "logging_email"
    
    # MongoDB (Email Content & Attachments)
    mongodb_url: str = "mongodb://localhost:27017/"
    mongodb_database: str = "logging_email"
    
    # RabbitMQ (Message Queue)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue: str = "email_processing"
    
    # Redis (Cache)
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300
    
    # Celery (Task Queue)
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # Security
    jwt_secret: str
    api_token_salt: str
    
    # Session & Auth
    access_token_lifetime_minutes: int = 15
    refresh_token_lifetime_days: int = 30
    session_absolute_limit_days: int = 90
    session_idle_limit_days: int = 30
    
    # SMTP (Outbound)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@logging.email"
    smtp_from_name: str = "logging.email"
    smtp_use_tls: bool = True
    
    # SMTP Backup
    smtp_backup_host: str = ""
    smtp_backup_port: int = 587
    smtp_backup_user: str = ""
    smtp_backup_password: str = ""
    smtp_backup_from_email: str = ""
    
    # Email Retry
    email_max_attempts: int = 5
    email_retry_base_delay: int = 60  # seconds
    email_expiry_hours: int = 48
    
    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_id: str
    
    # Application
    domain: str = "logging.email"
    backend_url: str = "https://api.logging.email"
    frontend_url: str = "https://logging.email"
    
    class Config:
        env_file = ".env"

settings = Settings()
