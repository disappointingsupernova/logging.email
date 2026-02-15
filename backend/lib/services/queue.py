import pika
import json
from config import settings

def get_rabbitmq_connection():
    """Get RabbitMQ connection"""
    params = pika.URLParameters(settings.rabbitmq_url)
    return pika.BlockingConnection(params)

def publish_message(message: dict):
    """Publish message to RabbitMQ queue"""
    connection = get_rabbitmq_connection()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=settings.rabbitmq_queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )
    finally:
        connection.close()

def consume_messages(callback):
    """Consume messages from RabbitMQ queue"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    
    def wrapper(ch, method, properties, body):
        message = json.loads(body)
        callback(message)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(
        queue=settings.rabbitmq_queue,
        on_message_callback=wrapper
    )
    
    channel.start_consuming()
