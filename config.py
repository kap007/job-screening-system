"""Configuration settings for the job screening system."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# RabbitMQ Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Queue Names
JD_QUEUE = "job_desc_queue"
JD_SUMMARY_QUEUE = "jd_summary_queue"
RESUME_QUEUE = "resume_queue"
RESUME_PROFILE_QUEUE = "resume_profile_queue"
MATCH_QUEUE = "match_queue"
EMAIL_QUEUE = "email_queue"

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///job_screening.db")

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama2:13b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "user@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")
EMAIL_FROM = os.getenv("EMAIL_FROM", "hr@example.com")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company")

# Matching Configuration
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.8"))  # 80% match required

# Input/Output Paths
JD_INPUT_DIR = os.getenv("JD_INPUT_DIR", "data/job_descriptions")
RESUME_INPUT_DIR = os.getenv("RESUME_INPUT_DIR", "data/resumes")