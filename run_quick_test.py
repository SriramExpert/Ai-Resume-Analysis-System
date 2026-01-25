#!/usr/bin/env python3
"""
Quick test script to run the system with sample data
"""

import os
import json
from src.tools.tool1_resume_parser import ResumeParser
from src.tools.tool2_comparison_engine import ComparisonEngine
from src.tools.tool3_blog_generator import BlogGenerator

def create_sample_resumes():
    """Create sample resume data for testing"""
    sample_dir = "data/resumes"
    os.makedirs(sample_dir, exist_ok=True)
    
    # Sample resume 1: Backend Developer
    resume1 = """John Smith
Senior Backend Developer
john.smith@email.com | (123) 456-7890 | LinkedIn: linkedin.com/in/johnsmith

SUMMARY
Senior Backend Developer with 8+ years of experience building scalable systems.
Expert in Python, Django, and AWS cloud services.

EXPERIENCE
Senior Backend Developer - TechCorp Inc. (2019-Present)
- Developed microservices using Python and FastAPI
- Implemented CI/CD pipelines with Jenkins and Docker
- Optimized database queries reducing response time by 40%
- Technologies: Python, FastAPI, PostgreSQL, AWS, Docker, Kubernetes

Backend Developer - StartupXYZ (2016-2019)
- Built REST APIs using Django REST Framework
- Implemented authentication systems with JWT
- Technologies: Python, Django, MySQL, Redis, Celery

EDUCATION
BS Computer Science - University of Technology (2016)

SKILLS
Programming: Python, JavaScript, SQL
Frameworks: Django, FastAPI, React
Tools: Git, Docker, Jenkins, AWS, Kubernetes
Databases: PostgreSQL, MySQL, Redis
Cloud: AWS (EC2, S3, RDS, Lambda)
Certifications: AWS Solutions Architect
"""
    
    # Sample resume 2: Full Stack Developer
    resume2 = """Sarah Johnson
Full Stack Developer
sarah.j@email.com | (987) 654-3210 | GitHub: github.com/sarahj

PROFILE
Full Stack Developer with 5 years of experience in modern web development.
Proficient in both frontend and backend technologies.

WORK EXPERIENCE
Full Stack Developer - Digital Solutions Co. (2020-Present)
- Developed full-stack applications using MERN stack
- Implemented responsive UIs with React and Material-UI
- Built Node.js backend services
- Technologies: JavaScript, React, Node.js, Express, MongoDB, GraphQL

Junior Developer - WebDev Agency (2018-2020)
- Created WordPress websites and custom themes
- Developed JavaScript plugins and extensions
- Technologies: PHP, JavaScript, WordPress, CSS, HTML

EDUCATION
BSc Software Engineering - State University (2018)

TECHNICAL SKILLS
Languages: JavaScript, TypeScript, Python, PHP
Frontend: React, Vue.js, HTML5, CSS3, SASS
Backend: Node.js, Express, Django
Databases: MongoDB, MySQL, PostgreSQL
Tools: Git, Webpack, Docker, Jest
Cloud: AWS, Firebase, Heroku
"""
    
    # Sample resume 3: DevOps Engineer
    resume3 = """Michael Chen
DevOps Engineer
michael.chen@email.com | (555) 123-4567

PROFESSIONAL SUMMARY
DevOps Engineer with 6 years of experience in cloud infrastructure and automation.
Expert in AWS, Kubernetes, and Infrastructure as Code.

EXPERIENCE
DevOps Engineer - CloudTech Ltd. (2019-Present)
- Managed Kubernetes clusters with 200+ microservices
- Implemented infrastructure as code using Terraform
- Built monitoring with Prometheus and Grafana
- Technologies: AWS, Kubernetes, Terraform, Ansible, Prometheus, Grafana

System Administrator - DataSystems Inc. (2017-2019)
- Managed Linux servers and network infrastructure
- Implemented backup and disaster recovery solutions
- Technologies: Linux, Bash, Python, Docker, Nagios

EDUCATION
MS Cloud Computing - Tech University (2017)
BS Information Technology - College of Tech (2015)

SKILLS & EXPERTISE
Cloud Platforms: AWS, Azure, GCP
Containerization: Docker, Kubernetes, Helm
Infrastructure as Code: Terraform, CloudFormation
CI/CD: Jenkins, GitLab CI, GitHub Actions
Monitoring: Prometheus, Grafana, ELK Stack
Scripting: Python, Bash, PowerShell
Certifications: AWS DevOps Professional, CKA
"""
    
    # Save sample resumes
    with open(os.path.join(sample_dir, "resume1_backend.txt"), "w") as f:
        f.write(resume1)
    
    with open(os.path.join(sample_dir, "resume2_fullstack.txt"), "w") as f:
        f.write(resume2)
    
    with open(os.path.join(sample_dir, "resume3_devops.txt"), "w") as f:
        f.write(resume3)
    
    print("✓ Created 3 sample resumes in data/resumes/")
    return [
        os.path.join(sample_dir, "resume1_backend.txt"),
        os.path.join(sample_dir, "resume2_fullstack.txt"),
        os.path.join(sample_dir, "resume3_devops.txt")
    ]

def quick_test():
    """Run a quick test of the system"""
    print("🚀 Quick Test: Resume Analysis System")
    print("=" * 50)
    
    # Create sample resumes if they don't exist
    resume_files = []
    for i in range(1, 4):
        txt_file = f"data/resumes/resume{i}.txt"
        pdf_file = f"data/resumes/resume{i}.pdf"
        if os.path.exists(txt_file) or os.path.exists(pdf_file):
            if os.path.exists(pdf_file):
                resume_files.append(pdf_file)
            else:
                resume_files.append(txt_file)
    
    if len(resume_files) < 3:
        print("Creating sample resumes...")
        resume_files = create_sample_resumes()
    
    print(f"\n📄 Analyzing resumes: {[os.path.basename(f) for f in resume_files]}")
    
    try:
        # Initialize tools
        parser = ResumeParser()
        comparator = ComparisonEngine()
        blog_gen = BlogGenerator()
        
        print("\n1️⃣  Parsing resumes...")
        resumes_data = parser.process_multiple_resumes(resume_files)
        
        print(f"\n✅ Parsed {len(resumes_data)} resumes")
        for i, data in enumerate(resumes_data):
            print(f"   Candidate {i+1}: {data.get('name', 'Unknown')}")
            print(f"   Tech Stack: {', '.join(data.get('tech_stack', [])[:5])}...")
        
        print("\n2️⃣  Comparing resumes...")
        comparison = comparator.compare_resumes(resumes_data)
        
        # Save comparison
        os.makedirs("outputs/comparisons", exist_ok=True)
        with open("outputs/comparisons/test_comparison.json", "w") as f:
            json.dump(comparison, f, indent=2)
        
        print("✅ Comparison saved to outputs/comparisons/test_comparison.json")
        
        print("\n3️⃣  Generating blog post...")
        blog_content = blog_gen.generate_blog_post(comparison, resumes_data)
        
        # Save blog
        os.makedirs("outputs/blog_posts", exist_ok=True)
        blog_path = "outputs/blog_posts/test_blog.md"
        with open(blog_path, "w") as f:
            f.write(blog_content)
        
        print(f"✅ Blog post saved to {blog_path}")
        
        # Show summary
        print("\n" + "=" * 50)
        print("📊 QUICK TEST RESULTS:")
        print("=" * 50)
        
        sim_score = comparison.get('similarity_analysis', {}).get('average_similarity', 0)
        print(f"Overall Similarity: {sim_score:.1%}")
        
        common_tech = comparison.get('llm_analysis', {}).get('tech_stack_comparison', {}).get('common_technologies', [])
        print(f"Common Technologies: {len(common_tech)}")
        if common_tech:
            print(f"  {', '.join(common_tech[:5])}...")
        
        print(f"\n📁 Outputs created in 'outputs/' directory")
        print("🎉 Quick test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during quick test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()