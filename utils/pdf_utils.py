"""Utilities for handling PDF files."""
import fitz  # PyMuPDF
import os
import re
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFParser:
    """Parser for PDF documents."""
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text content from a PDF file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            text = ""
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise
    
    @staticmethod
    def extract_basic_info(text: str) -> Dict[str, Any]:
        """
        Extract basic information from resume text using regex patterns.
        This is a basic implementation that can be used as a fallback or
        to supplement the LLM-based parsing.
        """
        # Initialize data structure for extracted info
        info = {
            "name": None,
            "email": None,
            "phone": None
        }
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            info["email"] = emails[0]
        
        # Phone pattern (various formats)
        phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
            r'\b\+\d{1,2}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'  # +1 123-456-7890
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                info["phone"] = phones[0]
                break
        
        # Try to extract name (this is more complex and less reliable)
        # First few lines of a resume often contain the name
        lines = text.split('\n')
        for i in range(min(5, len(lines))):
            line = lines[i].strip()
            # Skip empty lines or lines that are likely to be emails or phones
            if (line and '@' not in line and 
                not re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line) and
                len(line.split()) <= 4):  # Most names are 1-4 words
                info["name"] = line
                break
        
        return info
    
    @staticmethod
    def get_resume_metadata(pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            metadata = {}
            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata from PDF {pdf_path}: {e}")
            return {}