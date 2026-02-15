from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "logging_email"
    db_password: str
    db_name: str = "logging_email"
    mongodb_url: str = "mongodb://localhost:27017/"
    mongodb_database: str = "logging_email"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_queue: str = "email_processing"
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings()
