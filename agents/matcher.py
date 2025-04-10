"""Matcher Agent for matching candidates to job descriptions."""
import logging
import json
from typing import Dict, Any, Optional, Tuple
import threading
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RESUME_PROFILE_QUEUE, MATCH_QUEUE, EMAIL_QUEUE, MATCH_THRESHOLD
from models.embedding_manager import EmbeddingManager
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatcherAgent:
    """Agent for matching candidates to job descriptions."""
    
    def __init__(self, embedding_manager: Optional[EmbeddingManager] = None, 
                 db_manager: Optional[DatabaseManager] = None,
                 rabbitmq_client: Optional[RabbitMQClient] = None):
        """Initialize the agent."""
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.db_manager = db_manager or DatabaseManager()
        self.message_bus = rabbitmq_client or RabbitMQClient()
        self.match_threshold = MATCH_THRESHOLD
        logger.info("MatcherAgent initialized")
    
    def match_candidate_to_jobs(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match a candidate's profile to all active job descriptions.
        
        Expected resume_data format:
        {
            "candidate_id": 123,
            "resume_path": "/path/to/resume.pdf",
            "parsed_resume": {...}
        }
        """
        try:
            candidate_id = resume_data["candidate_id"]
            parsed_resume = resume_data["parsed_resume"]
            logger.info(f"Matching candidate {candidate_id} to available jobs")
            
            # Get all job descriptions from database
            # For a large system, we might want to limit this to "active" jobs
            # This is a simplified implementation assuming we have access to all job IDs
            
            # Get all job IDs (implementation depends on your database schema)
            # For now, let's assume we have a method to get all job IDs
            with self.db_manager.get_session() as session:
                from database.db_manager import JobDescription
                jobs = session.query(JobDescription).all()
                job_ids = [job.job_id for job in jobs]
            
            match_results = []
            
            # Match candidate against each job
            for job_id in job_ids:
                job_data = self.db_manager.get_job_description(job_id)
                if not job_data:
                    logger.warning(f"Job {job_id} not found in database")
                    continue
                
                # Calculate match score
                score, matching_details = self.embedding_manager.calculate_match_score(job_data, parsed_resume)
                
                # Save match to database
                match = self.db_manager.save_match(job_data["id"], candidate_id, score)
                
                # If score is above threshold, notify for email
                if score >= self.match_threshold:
                    # Prepare notification for email agent
                    email_data = {
                        "match_id": match.id,
                        "job_id": job_data["id"],
                        "job_title": job_data["job_title"],
                        "candidate_id": candidate_id,
                        "candidate_name": parsed_resume.get("name", "Candidate"),
                        "candidate_email": parsed_resume.get("contact", {}).get("email", ""),
                        "score": score,
                        "matching_details": matching_details
                    }
                    
                    # Publish to email queue
                    self.message_bus.publish_message(EMAIL_QUEUE, email_data)
                    logger.info(f"Candidate {candidate_id} qualified for job {job_id} with score {score:.2f}")
                
                # Add to results
                match_results.append({
                    "job_id": job_id,
                    "score": score,
                    "matching_details": matching_details,
                    "qualified": score >= self.match_threshold
                })
            
            # Publish overall match results
            result = {
                "candidate_id": candidate_id,
                "matches": match_results
            }
            self.message_bus.publish_message(MATCH_QUEUE, result)
            
            logger.info(f"Candidate {candidate_id} matched against {len(job_ids)} jobs")
            return result
            
        except Exception as e:
            logger.error(f"Error matching candidate {resume_data.get('candidate_id', 'unknown')}: {e}")
            # Could publish an error message to a separate error queue
            return {"error": str(e), "candidate_id": resume_data.get("candidate_id", "unknown")}
    
    def handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from the message bus."""
        logger.info(f"Received profile message for candidate: {message.get('candidate_id', 'unknown')}")
        self.match_candidate_to_jobs(message)
    
    def start(self):
        """Start the agent to listen for parsed resumes."""
        logger.info("Starting MatcherAgent")
        try:
            # Start consuming messages from the resume profile queue
            self.message_bus.start_consumer_thread(RESUME_PROFILE_QUEUE, self.handle_message)
            
            # Keep the agent running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("MatcherAgent stopped by user")
        except Exception as e:
            logger.error(f"Error in MatcherAgent: {e}")
        finally:
            # Clean up resources
            self.message_bus.close()

# For standalone testing/running
if __name__ == "__main__":
    agent = MatcherAgent()
    agent.start()