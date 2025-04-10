# job-screening-system
# Multi-Agent AI Framework for Automated Job Screening

This system implements a multi-agent AI framework for automating job applicant screening using LangChain and on-premises Ollama-hosted LLMs. The goal is to streamline the recruitment screening process by having specialized AI agents handle each step: summarizing job descriptions, parsing candidate resumes, matching profiles to job requirements via embeddings, and drafting personalized interview invitation emails for top matches.

## Architecture Overview

The system follows a multi-agent supervisor architecture where a central Orchestrator Agent oversees specialized sub-agents. The agents communicate through an event-driven message bus, allowing them to operate asynchronously and in parallel when appropriate.

### Components

1. **Job Description Summarizer Agent**: Extracts key information from job descriptions
2. **Resume Parser Agent**: Converts resumes into structured data profiles
3. **Matcher Agent**: Calculates similarity scores between candidates and jobs
4. **Email Agent**: Generates and sends interview invitation emails
5. **Orchestrator Agent**: Coordinates the overall workflow

### Workflow

1. A new job description CSV is uploaded to the `data/job_descriptions` directory
2. The Orchestrator detects the file and sends it to the JD Summarizer Agent
3. The JD Summarizer extracts key requirements and publishes the structured summary
4. New resumes (PDFs) are uploaded to the `data/resumes` directory
5. The Orchestrator sends them to the Resume Parser Agent
6. The Resume Parser extracts candidate information into structured profiles
7. The Matcher Agent calculates similarity scores between candidates and job requirements
8. For matches above the threshold (configurable, default 80%), the Email Agent generates and sends interview invitations

## Prerequisites

- Python 3.8+
- RabbitMQ server
- Ollama with LLama2 or similar LLM model

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/job-screening-system.git
cd job-screening-system
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Install and start RabbitMQ:
   - Follow the instructions at [RabbitMQ Installation Guide](https://www.rabbitmq.com/download.html)

4. Install and configure Ollama:
   - Follow the instructions at [Ollama Installation Guide](https://ollama.ai/)
   - Pull the necessary model: `ollama pull llama2:13b`

5. Create a `.env` file with your configuration:

```
# RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest

# Database Configuration
DATABASE_URL=sqlite:///job_screening.db

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama2:13b
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Email Configuration
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
EMAIL_FROM=hr@yourcompany.com
COMPANY_NAME=Your Company

# Matching Configuration
MATCH_THRESHOLD=0.8
```

## Usage

1. Create the input directories:

```bash
mkdir -p data/job_descriptions
mkdir -p data/resumes
```

2. Start the system:

```bash
python main.py
```

3. To run only specific components:

```bash
python main.py --mode orchestrator  # Only run the orchestrator
python main.py --mode jd  # Only run the JD Summarizer Agent
python main.py --mode resume  # Only run the Resume Parser Agent
python main.py --mode matcher  # Only run the Matcher Agent
python main.py --mode email  # Only run the Email Agent
```

4. Add job descriptions as CSV files to the `data/job_descriptions` directory.
   - Format: CSV with columns `job_id,job_title,job_description`

5. Add candidate resumes as PDF files to the `data/resumes` directory.

## Example Job Description CSV

```csv
job_id,job_title,job_description
job123,Software Engineer,"We are looking for a Software Engineer with experience in Python and machine learning. Responsibilities include developing new features, maintaining existing code, and collaborating with the data science team. Requirements: 3+ years of Python experience, knowledge of machine learning libraries, and a Bachelor's degree in Computer Science or related field."
```

## System Monitoring

The system logs all activities to `job_screening.log`. You can monitor the log file to see the progress and any errors:

```bash
tail -f job_screening.log
```

## Database

The system uses SQLite to store all data, including:
- Job descriptions and their summaries
- Candidate information and parsed resumes
- Match scores and email status

You can query the database directly using SQL tools or use the provided database manager functions in your code.

## Customization

- Adjust the matching threshold in the `.env` file
- Modify prompt templates in the LLM manager to customize how the system interprets job descriptions and resumes
- Change the embedding model to optimize for your specific domain

## License

This project is licensed under the MIT License - see the LICENSE file for details.
