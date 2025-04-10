"""Utilities for handling emails."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailSender:
    """Class for sending emails."""
    
    def __init__(self, smtp_server: str = SMTP_SERVER, 
                 smtp_port: int = SMTP_PORT,
                 smtp_user: str = SMTP_USER,
                 smtp_password: str = SMTP_PASSWORD,
                 email_from: str = EMAIL_FROM):
        """Initialize email sender with SMTP configuration."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from
        
        logger.info(f"EmailSender initialized with server: {smtp_server}:{smtp_port}")
    
    def send_email(self, to_email: str, subject: str, body: str, 
                   cc_list: Optional[List[str]] = None) -> bool:
        """Send an email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_list:
                msg['Cc'] = ", ".join(cc_list)
            
            # Attach body
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                
                # Prepare recipients
                recipients = [to_email]
                if cc_list:
                    recipients.extend(cc_list)
                
                # Send email
                server.sendmail(self.email_from, recipients, msg.as_string())
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_interview_invitation(self, to_email: str, candidate_name: str, 
                                 job_title: str, email_body: str) -> bool:
        """Send interview invitation email."""
        subject = f"Interview Invitation: {job_title} Position"
        
        return self.send_email(to_email, subject, email_body)