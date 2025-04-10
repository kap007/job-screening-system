"""Job Description Summarizer Agent."""
import logging
import json
from typing import Dict, Any, Optional
import threading
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import JD_QUEUE, JD_SUMMARY_QUEUE
from models.llm_manager import LLMManager
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JDSummarizerAgent:
    """Agent for summarizing job descriptions."""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 db_manager: Optional[DatabaseManager] = None,
                 rabbitmq_client: Optional[RabbitMQClient] = None):
        """Initialize the agent."""
        self.llm_manager = llm_manager or LLMManager()
        self.db_manager = db_manager or DatabaseManager()
        self.message_bus = rabbitmq_client or RabbitMQClient()
        logger.info("JDSummarizerAgent initialized")
    
    def summarize_job_description(self, jd_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process job description and create a summary.
        
        Expected jd_data format:
        {
            "job_id": "unique_job_id",
            "job_title": "Software Engineer",
            "raw_text": "Full job description text..."
        }
        """
        try:
            logger.info(f"Processing job description: {jd_data['job_id']}")
            
            # Extract the summary using LLM
            summary_data = self.llm_manager.summarize_job_description(jd_data["raw_text"])
            
            # Update the job title if it was extracted from the text
            if summary_data.get("job_title") and not jd_data.get("job_title"):
                jd_data["job_title"] = summary_data["job_title"]
            
            # Store the processed job description in the database
            self.db_manager.update_job_summary(
                jd_data["job_id"],
                summary_data["summary"],
                summary_data["skills"],
                summary_data["responsibilities"],
                summary_data["qualifications"]
            )
            
            # Prepare response with the summary and job ID
            result = {
                "job_id": jd_data["job_id"],
                "job_title": jd_data.get("job_title", summary_data.get("job_title", "")),
                "summary": summary_data["summary"],
                "skills": summary_data["skills"],
                "responsibilities": summary_data["responsibilities"],
                "qualifications": summary_data["qualifications"]
            }
            
            # Publish the summary to the message bus
            self.message_bus.publish_message(JD_SUMMARY_QUEUE, result)
            
            logger.info(f"Job description {jd_data['job_id']} summarized successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error summarizing job description {jd_data.get('job_id', 'unknown')}: {e}")
            # Could publish an error message to a separate error queue
            return {"error": str(e), "job_id": jd_data.get("job_id", "unknown")}
    
    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from the message bus."""
        logger.info(f"Received job description message: {message.get('job_id', 'unknown')}")
        self.summarize_job_description(message)
    
    def start(self):
        """Start the agent to listen for job descriptions."""
        logger.info("Starting JDSummarizerAgent")
        try:
            # Start consuming messages from the job description queue
            self.message_bus.start_consumer_thread(JD_QUEUE, self.handle_message)
            
            # Keep the agent running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("JDSummarizerAgent stopped by user")
        except Exception as e:
            logger.error(f"Error in JDSummarizerAgent: {e}")
        finally:
            # Clean up resources
            self.message_bus.close()

# For standalone testing/running
if __name__ == "__main__":
    agent = JDSummarizerAgent()
    agent.start()