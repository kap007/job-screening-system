"""Resume Parser Agent."""
import logging
import json
import os
from typing import Dict, Any, Optional
import threading
import time

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RESUME_QUEUE, RESUME_PROFILE_QUEUE
from models.llm_manager import LLMManager
from utils.pdf_utils import PDFParser
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeParserAgent:
    """Agent for parsing resumes."""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 db_manager: Optional[DatabaseManager] = None,
                 rabbitmq_client: Optional[RabbitMQClient] = None):
        """Initialize the agent."""
        self.llm_manager = llm_manager or LLMManager()
        self.db_manager = db_manager or DatabaseManager()
        self.message_bus = rabbitmq_client or RabbitMQClient()
        self.pdf_parser = PDFParser()
        logger.info("ResumeParserAgent initialized")
    
    def parse_resume(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process resume and extract structured data.
        
        Expected resume_data format:
        {
            "resume_path": "/path/to/resume.pdf",
            "candidate_id": 123  # Optional
        }
        """
        try:
            resume_path = resume_data["resume_path"]
            logger.info(f"Processing resume: {resume_path}")
            
            # Extract text from PDF
            resume_text = self.pdf_parser.extract_text_from_pdf(resume_path)
            
            # Extract basic info using regex as a backup
            basic_info = self.pdf_parser.extract_basic_info(resume_text)
            
            # Parse resume using LLM
            parsed_resume = self.llm_manager.parse_resume(resume_text)
            
            # Combine results, using LLM output but falling back to regex for missing fields
            if not parsed_resume.get("name") and basic_info.get("name"):
                parsed_resume["name"] = basic_info["name"]
            
            if not parsed_resume.get("contact", {}).get("email") and basic_info.get("email"):
                if "contact" not in parsed_resume:
                    parsed_resume["contact"] = {}
                parsed_resume["contact"]["email"] = basic_info["email"]
            
            if not parsed_resume.get("contact", {}).get("phone") and basic_info.get("phone"):
                if "contact" not in parsed_resume:
                    parsed_resume["contact"] = {}
                parsed_resume["contact"]["phone"] = basic_info["phone"]
            
            # Store or create candidate in database
            candidate_id = resume_data.get("candidate_id")
            if candidate_id:
                # Update existing candidate
                self.db_manager.update_candidate_resume(candidate_id, parsed_resume)
            else:
                # Create new candidate
                candidate = self.db_manager.save_candidate(
                    name=parsed_resume.get("name", "Unknown"),
                    email=parsed_resume.get("contact", {}).get("email", ""),
                    phone=parsed_resume.get("contact", {}).get("phone", ""),
                    resume_path=resume_path
                )
                candidate_id = candidate.id
                self.db_manager.update_candidate_resume(candidate_id, parsed_resume)
            
            # Prepare result with parsed data and candidate ID
            result = {
                "candidate_id": candidate_id,
                "resume_path": resume_path,
                "parsed_resume": parsed_resume
            }
            
            # Publish parsed resume to the message bus
            self.message_bus.publish_message(RESUME_PROFILE_QUEUE, result)
            
            logger.info(f"Resume for candidate {candidate_id} parsed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing resume {resume_data.get('resume_path', 'unknown')}: {e}")
            # Could publish an error message to a separate error queue
            return {"error": str(e), "resume_path": resume_data.get("resume_path", "unknown")}
    
    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from the message bus."""
        logger.info(f"Received resume message: {message.get('resume_path', 'unknown')}")
        self.parse_resume(message)
    
    def start(self):
        """Start the agent to listen for resumes."""
        logger.info("Starting ResumeParserAgent")
        try:
            # Start consuming messages from the resume queue
            self.message_bus.start_consumer_thread(RESUME_QUEUE, self.handle_message)
            
            # Keep the agent running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("ResumeParserAgent stopped by user")
        except Exception as e:
            logger.error(f"Error in ResumeParserAgent: {e}")
        finally:
            # Clean up resources
            self.message_bus.close()

# For standalone testing/running
if __name__ == "__main__":
    agent = ResumeParserAgent()
    agent.start()