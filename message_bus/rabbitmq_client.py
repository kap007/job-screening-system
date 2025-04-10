"""RabbitMQ client for message bus."""
import pika
import json
import logging
from typing import Dict, Any, Callable, Optional
import threading
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS,
    JD_QUEUE, JD_SUMMARY_QUEUE, RESUME_QUEUE, RESUME_PROFILE_QUEUE,
    MATCH_QUEUE, EMAIL_QUEUE
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Client for RabbitMQ operations."""
    
    def __init__(self):
        """Initialize RabbitMQ connection."""
        self.connection = None
        self.channel = None
        self.connect()
        
        # Define all queues that the system will use
        self.queues = [
            JD_QUEUE,
            JD_SUMMARY_QUEUE,
            RESUME_QUEUE,
            RESUME_PROFILE_QUEUE,
            MATCH_QUEUE,
            EMAIL_QUEUE
        ]
        self.declare_queues()
    
    def connect(self):
        """Connect to RabbitMQ server."""
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def reconnect(self):
        """Reconnect to RabbitMQ if connection is lost."""
        if self.connection is None or self.connection.is_closed:
            logger.info("Attempting to reconnect to RabbitMQ")
            retry_count = 0
            while retry_count < 5:
                try:
                    self.connect()
                    self.declare_queues()
                    return True
                except Exception as e:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(f"Reconnect attempt {retry_count} failed: {e}. Retrying in {wait_time}s")
                    time.sleep(wait_time)
            logger.critical("Failed to reconnect to RabbitMQ after multiple attempts")
            return False
        return True
    
    def declare_queues(self):
        """Declare all necessary queues."""
        try:
            for queue in self.queues:
                self.channel.queue_declare(queue=queue, durable=True)
            logger.info("All queues declared successfully")
        except Exception as e:
            logger.error(f"Failed to declare queues: {e}")
            raise
    
    def publish_message(self, queue: str, message: Dict[str, Any]):
        """Publish a message to a queue."""
        try:
            if not self.reconnect():
                raise Exception("Cannot publish: RabbitMQ connection unavailable")
                
            message_json = json.dumps(message)
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=message_json,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            logger.info(f"Published message to {queue}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {queue}: {e}")
            return False
    
    def consume_messages(self, queue: str, callback: Callable):
        """Consume messages from a queue with a callback function."""
        if not self.reconnect():
            raise Exception("Cannot consume: RabbitMQ connection unavailable")
            
        # Define the callback wrapper to handle message processing
        def callback_wrapper(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Negative acknowledgment, message will be requeued
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # Set up the consumer
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=queue,
            on_message_callback=callback_wrapper
        )
        
        logger.info(f"Started consuming messages from {queue}")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consume_messages: {e}")
            self.channel.stop_consuming()
    
    def start_consumer_thread(self, queue: str, callback: Callable):
        """Start a consumer in a separate thread."""
        thread = threading.Thread(
            target=self.consume_messages,
            args=(queue, callback),
            daemon=True
        )
        thread.start()
        return thread
    
    def close(self):
        """Close the connection to RabbitMQ."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")