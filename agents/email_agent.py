"""Email Agent for sending interview invitations."""
import logging
import json
from typing import Dict, Any, Optional
import threading
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMAIL_QUEUE, COMPANY_NAME
from models.llm_manager import LLMManager
from utils.email_utils import EmailSender
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailAgent:
    """Agent for sending interview invitation emails."""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 db_manager: Optional[DatabaseManager] = None,
                 rabbitmq_client: Optional[RabbitMQClient] = None,
                 email_sender: Optional[EmailSender] = None):
        """Initialize the agent."""
        self.llm_manager = llm_manager or LLMManager()
        self.db_manager = db_manager or DatabaseManager()
        self.message_bus = rabbitmq_client or RabbitMQClient()
        self.email_sender = email_sender or EmailSender()
        self.company_name = COMPANY_NAME
        logger.info("EmailAgent initialized")
    
    def send_interview_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and send interview invitation email.
        
        Expected email_data format:
        {
            "match_id": 456,
            "job_id": 789,
            "job_title": "Software Engineer",
            "candidate_id": 123,
            "candidate_name": "Jane Doe",
            "candidate_email": "jane.doe@example.com",
            "score": 0.85,
            "matching_details": {...}
        }
        """
        try:
            match_id = email_data["match_id"]
            candidate_name = email_data["candidate_name"]
            candidate_email = email_data["candidate_email"]
            job_title = email_data["job_title"]
            
            logger.info(f"Generating email for match {match_id} (Candidate: {candidate_name}, Job: {job_title})")
            
            # Generate email content using LLM
            email_body = self.llm_manager.generate_email(
                candidate_name=candidate_name,
                job_title=job_title,
                company_name=self.company_name,
                match_details=email_data["matching_details"]
            )
            
            # Send the email
            sent = self.email_sender.send_interview_invitation(
                to_email=candidate_email,
                candidate_name=candidate_name,
                job_title=job_title,
                email_body=email_body
            )
            
            # Update the match record in the database if email was sent
            if sent:
                self.db_manager.update_match_email_sent(match_id)
                logger.info(f"Interview invitation email sent to {candidate_name} <{candidate_email}>")
            else:
                logger.error(f"Failed to send email to {candidate_name} <{candidate_email}>")
            
            # Prepare result
            result = {
                "match_id": match_id,
                "candidate_id": email_data["candidate_id"],
                "job_id": email_data["job_id"],
                "email_sent": sent,
                "email_body": email_body
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending interview email for match {email_data.get('match_id', 'unknown')}: {e}")
            # Could publish an error message to a separate error queue
            return {"error": str(e), "match_id": email_data.get("match_id", "unknown")}
    
    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from the message bus."""
        logger.info(f"Received email request for match: {message.get('match_id', 'unknown')}")
        self.send_interview_email(message)
    
    def start(self):
        """Start the agent to listen for email requests."""
        logger.info("Starting EmailAgent")
        try:
            # Start consuming messages from the email queue
            self.message_bus.start_consumer_thread(EMAIL_QUEUE, self.handle_message)
            
            # Keep the agent running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("EmailAgent stopped by user")
        except Exception as e:
            logger.error(f"Error in EmailAgent: {e}")
        finally:
            # Clean up resources
            self.message_bus.close()

# For standalone testing/running
if __name__ == "__main__":
    agent = EmailAgent()
    agent.start()