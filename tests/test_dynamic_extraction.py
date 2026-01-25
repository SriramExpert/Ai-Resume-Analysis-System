import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_integration.llm_handler import LLMHandler

def test_dynamic_extraction():
    load_dotenv()
    handler = LLMHandler()
    
    # Test case 1: Technical Resume
    tech_resume = """
    John Doe
    Software Engineer with 5 years of experience in Python and AWS.
    Experience: 
    - Senior Dev at TechCorp (2020-Present): Lead backend team, used FastAPI, PostgreSQL.
    - Junior Dev at StartUp (2018-2020): Built web apps with React.
    Education: BS in Computer Science from MIT.
    """
    
    print("\n--- Testing Technical Resume ---")
    data_tech = handler.extract_resume_info(tech_resume)
    print(f"Document Type: {data_tech.get('document_type')}")
    print(f"Candidate: {data_tech.get('candidate_name')}")
    print(f"Keys Extracted: {list(data_tech.keys())}")
    
    # Test case 2: Medical CV (Non-technical)
    medical_cv = """
    Dr. Jane Smith, MD
    Cardiologist specialize in non-invasive imaging.
    Work History:
    - Attending Physician, City General Hospital (2015-2023)
    - Resident, Mayo Clinic (2010-2015)
    Certifications: Board Certified in Cardiovascular Disease.
    Skills: Echocardiography, MRI, Patient Care.
    """
    
    print("\n--- Testing Medical CV ---")
    data_med = handler.extract_resume_info(medical_cv)
    print(f"Document Type: {data_med.get('document_type')}")
    print(f"Candidate: {data_med.get('candidate_name') or data_med.get('subject_name')}")
    print(f"Keys Extracted: {list(data_med.keys())}")

if __name__ == "__main__":
    test_dynamic_extraction()
