import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.models import ServiceHealth
from lib.database import get_db
from config import settings
import redis
import pika
from pymongo import MongoClient

def check_mysql() -> dict:
    """Check MySQL connectivity and response time"""
    start = time.time()
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        response_time = int((time.time() - start) * 1000)
        return {"status": "healthy", "response_time_ms": response_time, "error": None}
    except Exception as e:
        return {"status": "down", "response_time_ms": None, "error": str(e)}

def check_redis() -> dict:
    """Check Redis connectivity and response time"""
    start = time.time()
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        response_time = int((time.time() - start) * 1000)
        return {"status": "healthy", "response_time_ms": response_time, "error": None}
    except Exception as e:
        return {"status": "down", "response_time_ms": None, "error": str(e)}

def check_rabbitmq() -> dict:
    """Check RabbitMQ connectivity and response time"""
    start = time.time()
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        connection.close()
        response_time = int((time.time() - start) * 1000)
        return {"status": "healthy", "response_time_ms": response_time, "error": None}
    except Exception as e:
        return {"status": "down", "response_time_ms": None, "error": str(e)}

def check_mongodb() -> dict:
    """Check MongoDB connectivity and response time"""
    start = time.time()
    try:
        client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        client.server_info()
        response_time = int((time.time() - start) * 1000)
        return {"status": "healthy", "response_time_ms": response_time, "error": None}
    except Exception as e:
        return {"status": "down", "response_time_ms": None, "error": str(e)}

def check_all_services() -> dict:
    """Check all services and return status"""
    services = {
        "mysql": check_mysql(),
        "redis": check_redis(),
        "rabbitmq": check_rabbitmq(),
        "mongodb": check_mongodb()
    }
    
    # Log to database
    db = next(get_db())
    for service_name, result in services.items():
        health = ServiceHealth(
            service_name=service_name,
            status=result["status"],
            response_time_ms=result["response_time_ms"],
            error_message=result["error"]
        )
        db.add(health)
    
    try:
        db.commit()
    except:
        pass  # Don't fail if we can't log
    
    # Determine overall status
    all_healthy = all(s["status"] == "healthy" for s in services.values())
    any_down = any(s["status"] == "down" for s in services.values())
    
    overall = "healthy" if all_healthy else ("down" if any_down else "degraded")
    
    return {
        "status": overall,
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_service_health_history(service_name: str = None, hours: int = 24) -> list:
    """Get service health history"""
    db = next(get_db())
    from datetime import timedelta
    
    query = db.query(ServiceHealth).filter(
        ServiceHealth.checked_at > datetime.utcnow() - timedelta(hours=hours)
    )
    
    if service_name:
        query = query.filter(ServiceHealth.service_name == service_name)
    
    return query.order_by(ServiceHealth.checked_at.desc()).all()
