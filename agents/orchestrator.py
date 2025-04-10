"""Orchestrator Agent to coordinate the entire workflow."""
import logging
import json
import os
import time
import csv
from typing import Dict, Any, List, Optional
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    JD_QUEUE, RESUME_QUEUE, 
    JD_INPUT_DIR, RESUME_INPUT_DIR
)
from database.db_manager import DatabaseManager
from message_bus.rabbitmq_client import RabbitMQClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobDescriptionHandler(FileSystemEventHandler):
    """Handler for job description CSV file events."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            logger.info(f"New JD CSV detected: {event.src_path}")
            self.orchestrator.process_jd_file(event.src_path)

class ResumeHandler(FileSystemEventHandler):
    """Handler for resume PDF file events."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            logger.info(f"New resume PDF detected: {event.src_path}")
            self.orchestrator.process_resume_file(event.src_path)

class OrchestratorAgent:
    """Agent for orchestrating the job screening workflow."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None,
                 rabbitmq_client: Optional[RabbitMQClient] = None):
        """Initialize the agent."""
        self.db_manager = db_manager or DatabaseManager()
        self.message_bus = rabbitmq_client or RabbitMQClient()
        
        # Create input directories if they don't exist
        os.makedirs(JD_INPUT_DIR, exist_ok=True)
        os.makedirs(RESUME_INPUT_DIR, exist_ok=True)
        
        # Set up file system watchers
        self.jd_observer = None
        self.resume_observer = None
        
        logger.info("OrchestratorAgent initialized")
    
    def process_jd_file(self, file_path: str):
        """Process a job description CSV file."""
        try:
            logger.info(f"Processing JD file: {file_path}")
            
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    # Extract job data from CSV row
                    # Expected CSV columns: job_id, job_title, job_description
                    job_id = row.get('job_id', f"job_{int(time.time())}")
                    job_title = row.get('job_title', '')
                    job_description = row.get('job_description', '')
                    
                    if not job_description:
                        logger.warning(f"Empty job description for job_id: {job_id}")
                        continue
                    
                    # Save to database first
                    self.db_manager.save_job_description(job_id, job_title, job_description)
                    
                    # Send to JD Summarizer via message bus
                    jd_message = {
                        "job_id": job_id,
                        "job_title": job_title,
                        "raw_text": job_description
                    }
                    self.message_bus.publish_message(JD_QUEUE, jd_message)
                    
                    logger.info(f"Job {job_id} sent to JD Summarizer")
            
            # Optionally move or archive the processed file
            processed_dir = os.path.join(os.path.dirname(file_path), "processed")
            os.makedirs(processed_dir, exist_ok=True)
            
            new_path = os.path.join(processed_dir, os.path.basename(file_path))
            os.rename(file_path, new_path)
            logger.info(f"Moved processed file to {new_path}")
            
        except Exception as e:
            logger.error(f"Error processing JD file {file_path}: {e}")
    
    def process_resume_file(self, file_path: str):
        """Process a resume PDF file."""
        try:
            logger.info(f"Processing resume file: {file_path}")
            
            # Send to Resume Parser via message bus
            resume_message = {
                "resume_path": file_path
            }
            self.message_bus.publish_message(RESUME_QUEUE, resume_message)
            
            logger.info(f"Resume {file_path} sent to Resume Parser")
            
            # Note: We don't move or archive the resume file yet, as the resume parser
            # needs to access it. The resume parser could be responsible for moving
            # it after processing, or we could implement a more sophisticated approach
            # with a status database.
            
        except Exception as e:
            logger.error(f"Error processing resume file {file_path}: {e}")
    
    def process_existing_files(self):
        """Process any existing files in the input directories."""
        # Process existing JD files
        for filename in os.listdir(JD_INPUT_DIR):
            if filename.endswith('.csv'):
                file_path = os.path.join(JD_INPUT_DIR, filename)
                logger.info(f"Found existing JD file: {file_path}")
                self.process_jd_file(file_path)
        
        # Process existing resume files
        for filename in os.listdir(RESUME_INPUT_DIR):
            if filename.endswith('.pdf'):
                file_path = os.path.join(RESUME_INPUT_DIR, filename)
                logger.info(f"Found existing resume file: {file_path}")
                self.process_resume_file(file_path)
    
    def start_file_watchers(self):
        """Start watching for new job description and resume files."""
        # Set up JD file watcher
        jd_handler = JobDescriptionHandler(self)
        self.jd_observer = Observer()
        self.jd_observer.schedule(jd_handler, JD_INPUT_DIR, recursive=False)
        self.jd_observer.start()
        logger.info(f"Started watching for new JD files in {JD_INPUT_DIR}")
        
        # Set up resume file watcher
        resume_handler = ResumeHandler(self)
        self.resume_observer = Observer()
        self.resume_observer.schedule(resume_handler, RESUME_INPUT_DIR, recursive=False)
        self.resume_observer.start()
        logger.info(f"Started watching for new resume files in {RESUME_INPUT_DIR}")
    
    def start(self):
        """Start the orchestrator agent."""
        logger.info("Starting OrchestratorAgent")
        try:
            # Process any existing files
            self.process_existing_files()
            
            # Start watching for new files
            self.start_file_watchers()
            
            # Keep the agent running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("OrchestratorAgent stopped by user")
        except Exception as e:
            logger.error(f"Error in OrchestratorAgent: {e}")
        finally:
            # Stop file watchers
            if self.jd_observer:
                self.jd_observer.stop()
                self.jd_observer.join()
            
            if self.resume_observer:
                self.resume_observer.stop()
                self.resume_observer.join()
            
            # Clean up resources
            self.message_bus.close()

# For standalone testing/running
if __name__ == "__main__":
    agent = OrchestratorAgent()
    agent.start()