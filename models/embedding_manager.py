"""Embedding Manager for handling text embeddings."""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Tuple
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMBEDDING_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Manager for creating embeddings and calculating similarity."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        """Initialize embedding model."""
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        logger.info(f"Embedding Manager initialized with model: {model_name}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        return self.model.encode(text)
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Ensure embeddings are normalized
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)
        return float(similarity)
    
    def calculate_match_score(self, jd_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate match score between job description and resume.
        Returns a tuple with (score, matching_details)
        """
        # Prepare job description text
        jd_text = f"""
        Job Title: {jd_data.get('job_title', '')}
        
        Requirements:
        {' '.join(jd_data.get('qualifications', []))}
        
        Skills Required:
        {' '.join(jd_data.get('skills', []))}
        
        Responsibilities:
        {' '.join(jd_data.get('responsibilities', []))}
        """
        
        # Prepare resume text
        resume_skills = ' '.join(resume_data.get('skills', []))
        resume_experience = ' '.join([f"{exp.get('role', '')} at {exp.get('company', '')}: {exp.get('description', '')}" 
                                     for exp in resume_data.get('experience', [])])
        resume_education = ' '.join([f"{edu.get('degree', '')} from {edu.get('institution', '')}" 
                                    for edu in resume_data.get('education', [])])
        
        resume_text = f"""
        Skills:
        {resume_skills}
        
        Experience:
        {resume_experience}
        
        Education:
        {resume_education}
        """
        
        # Generate embeddings
        jd_embedding = self.get_embedding(jd_text)
        resume_embedding = self.get_embedding(resume_text)
        
        # Calculate cosine similarity
        similarity = self.cosine_similarity(jd_embedding, resume_embedding)
        
        # Find matching skills (simple overlap for demonstration)
        jd_skills = set([skill.lower() for skill in jd_data.get('skills', [])])
        resume_skills_set = set([skill.lower() for skill in resume_data.get('skills', [])])
        matching_skills = jd_skills.intersection(resume_skills_set)
        
        matching_details = {
            "matching_skills": list(matching_skills),
            "skill_match_percentage": len(matching_skills) / len(jd_skills) if jd_skills else 0,
            "overall_similarity": similarity
        }
        
        # Score is a weighted combination 
        # 70% from semantic similarity, 30% from direct skill matches
        final_score = 0.7 * similarity + 0.3 * matching_details["skill_match_percentage"]
        
        return final_score, matching_details