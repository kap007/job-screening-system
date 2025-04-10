"""LLM Manager for interacting with Ollama."""
from langchain.prompts import PromptTemplate
from langchain_ollama import Ollama
from langchain.chains import LLMChain
from typing import Dict, Any, List
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OLLAMA_BASE_URL, LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMManager:
    """Manager for LLM operations using Ollama."""
    
    def __init__(self, model_name: str = LLM_MODEL, base_url: str = OLLAMA_BASE_URL):
        """Initialize LLM model."""
        self.model_name = model_name
        self.base_url = base_url
        self.llm = Ollama(model=model_name, base_url=base_url)
        logger.info(f"LLM Manager initialized with model: {model_name}")
    
    def create_chain(self, prompt_template: str, output_key: str = "result") -> LLMChain:
        """Create an LLM chain with the given prompt template."""
        prompt = PromptTemplate.from_template(prompt_template)
        chain = LLMChain(llm=self.llm, prompt=prompt, output_key=output_key)
        return chain
    
    def summarize_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Summarize job description."""
        prompt_template = """
        You are a hiring specialist AI tasked with summarizing job descriptions. 
        Given the following job description, extract and organize these key elements:
        
        1. Job Title
        2. Key Responsibilities (list the main tasks and duties)
        3. Required Skills (technical skills, tools, languages, etc.)
        4. Required Qualifications (education, certifications, experience level)
        
        Format your response as structured text with clear headings. Make sure to capture all important requirements.
        
        Job Description:
        {jd_text}
        
        Summary:
        """
        
        chain = self.create_chain(prompt_template, "summary")
        result = chain.invoke({"jd_text": jd_text})
        
        # Parse the summary into structured data
        lines = result["summary"].strip().split("\n")
        summary_data = {
            "summary": result["summary"],
            "job_title": "",
            "responsibilities": [],
            "skills": [],
            "qualifications": []
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "Job Title:" in line:
                summary_data["job_title"] = line.replace("Job Title:", "").strip()
                current_section = None
            elif "Responsibilities:" in line or "Key Responsibilities:" in line:
                current_section = "responsibilities"
            elif "Required Skills:" in line or "Skills:" in line:
                current_section = "skills"
            elif "Required Qualifications:" in line or "Qualifications:" in line:
                current_section = "qualifications"
            elif current_section and line.startswith("- "):
                summary_data[current_section].append(line[2:].strip())
            elif current_section:
                summary_data[current_section].append(line)
        
        return summary_data
    
    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """Parse resume into structured data."""
        prompt_template = """
        You are a resume parsing AI. Given the following resume text, extract these key elements:
        
        1. Full Name
        2. Contact Information (email and phone)
        3. Education (list of degrees, institutions, and years)
        4. Work Experience (list of roles, companies, years, and key achievements)
        5. Skills (technical skills, languages, tools, etc.)
        6. Certifications (if any)
        7. Notable Achievements (if any)
        
        Format your response as a structured JSON object with these fields. Make sure to capture all important information.
        
        Resume Text:
        {resume_text}
        
        Parsed Resume (JSON format):
        """
        
        chain = self.create_chain(prompt_template, "parsed_resume")
        result = chain.invoke({"resume_text": resume_text})
        
        # Process the result to ensure it's proper JSON
        try:
            # Clean the output if it contains any markdown code block markers
            parsed_text = result["parsed_resume"].replace("```json", "").replace("```", "").strip()
            import json
            parsed_resume = json.loads(parsed_text)
            return parsed_resume
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing resume JSON: {e}")
            # Fallback: return basic structured data from the raw text
            return {
                "raw_text": result["parsed_resume"],
                "error": "Failed to parse as JSON"
            }
    
    def generate_email(self, candidate_name: str, job_title: str, company_name: str, 
                       match_details: Dict[str, Any]) -> str:
        """Generate interview invitation email."""
        prompt_template = """
        You are a hiring manager at {company_name}. Write a professional email inviting {candidate_name} to interview for the {job_title} position.
        
        The candidate's resume showed strong alignment with the job requirements, particularly in these areas:
        {match_details}
        
        Keep the email friendly but professional. Include:
        1. A personalized greeting
        2. Brief introduction about the position
        3. Mention why their skills match the job (be specific using the match details)
        4. Request for an interview and suggestion to schedule (no specific dates, they'll respond with availability)
        5. A professional closing
        
        Write the complete email with subject line, greeting, body and signature.
        """
        
        # Convert match details to a string
        match_str = "\n".join([f"- {k}: {v}" for k, v in match_details.items()])
        
        chain = self.create_chain(prompt_template, "email")
        result = chain.invoke({
            "candidate_name": candidate_name,
            "job_title": job_title,
            "company_name": company_name,
            "match_details": match_str
        })
        
        return result["email"]