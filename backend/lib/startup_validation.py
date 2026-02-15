"""Backend startup validation"""

from pathlib import Path

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(__file__).parent.parent / '.env'
    return env_path.exists()

def validate_config():
    """Validate configuration"""
    from config import settings
    
    errors = []
    
    if settings.jwt_secret == "CHANGE_ME_LONG_RANDOM_STRING":
        errors.append("JWT_SECRET not configured")
    
    if settings.api_token_salt == "CHANGE_ME_ANOTHER_RANDOM_STRING":
        errors.append("API_TOKEN_SALT not configured")
    
    if settings.db_password == "CHANGE_ME":
        errors.append("DB_PASSWORD not configured")
    
    if errors:
        raise RuntimeError(f"Configuration errors: {', '.join(errors)}")
    
    return True

def check_mysql():
    """Check MySQL connectivity"""
    try:
        from config import settings
        import pymysql
        
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            connect_timeout=5
        )
        conn.close()
        return True
    except Exception:
        return False

def check_redis():
    """Check Redis connectivity"""
    try:
        from config import settings
        import redis
        
        r = redis.from_url(settings.redis_url, socket_connect_timeout=5)
        r.ping()
        return True
    except Exception:
        return False

def check_mongodb():
    """Check MongoDB connectivity"""
    try:
        from config import settings
        from pymongo import MongoClient
        
        client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        client.server_info()
        return True
    except Exception:
        return False

def check_rabbitmq():
    """Check RabbitMQ connectivity"""
    try:
        from config import settings
        import pika
        
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        connection.close()
        return True
    except Exception:
        return False

def run_validation():
    """Run all validation checks"""
    if not check_env_file():
        raise RuntimeError(".env file not found")
    
    validate_config()
    
    if not check_mysql():
        raise RuntimeError("MySQL connection failed")
    
    if not check_redis():
        raise RuntimeError("Redis connection failed")
    
    if not check_mongodb():
        raise RuntimeError("MongoDB connection failed")
    
    if not check_rabbitmq():
        raise RuntimeError("RabbitMQ connection failed")
