"""Main entry point for the job screening system."""
import argparse
import logging
import os
import time
import threading
from typing import List, Dict, Any

from agents.orchestrator import OrchestratorAgent
from agents.jd_summarizer import JDSummarizerAgent
from agents.resume_parser import ResumeParserAgent
from agents.matcher import MatcherAgent
from agents.email_agent import EmailAgent
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("job_screening.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start_agent(agent_cls, name, **kwargs):
    """Start an agent in a separate thread."""
    logger.info(f"Starting {name}...")
    agent = agent_cls(**kwargs)
    thread = threading.Thread(target=agent.start, daemon=True)
    thread.start()
    return thread, agent

def main():
    """Run the entire job screening system."""
    parser = argparse.ArgumentParser(description="Job Screening System")
    parser.add_argument("--mode", choices=["all", "orchestrator", "jd", "resume", "matcher", "email"],
                      default="all", help="Which components to run")
    args = parser.parse_args()
    
    # Shared resources
    db_manager = DatabaseManager()
    rabbitmq_client = RabbitMQClient()
    
    threads = []
    agents = {}
    
    try:
        # Start agents based on mode
        if args.mode in ["all", "jd"]:
            thread, agent = start_agent(JDSummarizerAgent, "JD Summarizer Agent", 
                                      db_manager=db_manager, rabbitmq_client=rabbitmq_client)
            threads.append(thread)
            agents["jd"] = agent
        
        if args.mode in ["all", "resume"]:
            thread, agent = start_agent(ResumeParserAgent, "Resume Parser Agent", 
                                      db_manager=db_manager, rabbitmq_client=rabbitmq_client)
            threads.append(thread)
            agents["resume"] = agent
        
        if args.mode in ["all", "matcher"]:
            thread, agent = start_agent(MatcherAgent, "Matcher Agent", 
                                      db_manager=db_manager, rabbitmq_client=rabbitmq_client)
            threads.append(thread)
            agents["matcher"] = agent
        
        if args.mode in ["all", "email"]:
            thread, agent = start_agent(EmailAgent, "Email Agent", 
                                      db_manager=db_manager, rabbitmq_client=rabbitmq_client)
            threads.append(thread)
            agents["email"] = agent
        
        # The orchestrator should start last
        if args.mode in ["all", "orchestrator"]:
            thread, agent = start_agent(OrchestratorAgent, "Orchestrator Agent", 
                                      db_manager=db_manager, rabbitmq_client=rabbitmq_client)
            threads.append(thread)
            agents["orchestrator"] = agent
            
        # Keep the main thread running
        logger.info("Job Screening System is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Job Screening System...")
    except Exception as e:
        logger.error(f"Error in Job Screening System: {e}")
    finally:
        # Clean up
        for thread in threads:
            thread.join(timeout=1.0)
        
        if rabbitmq_client:
            rabbitmq_client.close()
        
        logger.info("Job Screening System stopped")

if __name__ == "__main__":
    main()