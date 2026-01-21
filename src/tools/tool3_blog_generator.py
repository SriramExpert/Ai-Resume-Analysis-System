import os
import markdown
from datetime import datetime
from typing import Dict, List, Any
from src.utils.file_handlers import FileHandler
from src.llm_integration.llm_handler import LLMHandler

class BlogGenerator:
    """Tool 3: Generate blog post from comparison analysis"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        self.llm_handler = LLMHandler(config_path)
        self.file_handler = FileHandler()
    
    def generate_blog_post(self, comparison_data: Dict, resumes_data: List[Dict], 
                          template: str = "professional") -> str:
        """Generate a blog post from comparison data"""
        
        print("Generating blog post...")
        
        # Get LLM-generated blog content
        blog_content = self.llm_handler.generate_blog_post(comparison_data, resumes_data)
        
        # Enhance with templates and formatting
        enhanced_blog = self._enhance_blog_content(blog_content, comparison_data, resumes_data, template)
        
        return enhanced_blog
    
    def _enhance_blog_content(self, blog_content: str, comparison_data: Dict, 
                             resumes_data: List[Dict], template: str) -> str:
        """Enhance blog content with templates and additional data"""
        
        # Extract key information for templates
        candidates = [resume.get('name', f'Candidate {i+1}') for i, resume in enumerate(resumes_data)]
        date = datetime.now().strftime("%B %d, %Y")
        
        if template == "professional":
            header = self._create_professional_header(candidates, date)
            footer = self._create_professional_footer()
        elif template == "technical":
            header = self._create_technical_header(candidates, date)
            footer = self._create_technical_footer()
        else:
            header = f"# Resume Comparison Analysis\n\n*Generated on {date}*\n\n"
            footer = "\n\n---\n*Analysis generated automatically using AI*"
        
        # Add executive summary
        summary = self._create_executive_summary(comparison_data, candidates)
        
        # Combine all parts
        enhanced_content = header + summary + blog_content + footer
        
        return enhanced_content
    
    def _create_professional_header(self, candidates: List[str], date: str) -> str:
        """Create professional blog header"""
        
        candidates_list = "\n".join([f"- **{c}**" for c in candidates])
        
        header = f"""# Comparative Analysis of Technical Talent: Insights from Resume Evaluation

*Published: {date}*

### Overview
This analysis compares {len(candidates)} technical professionals based on their resumes, providing insights for hiring managers, 
recruiters, and technical leaders. The evaluation focuses on technical skills, experience patterns, and unique value propositions.

**Candidates Analyzed:**
{candidates_list}

---

"""
        return header
    
    def _create_technical_header(self, candidates: List[str], date: str) -> str:
        """Create technical blog header"""
        
        candidates_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])
        
        header = f"""# Technical Resume Analysis: Comparing Three Software Professionals

*Analysis Date: {date}*

### Executive Brief
Automated comparison of {len(candidates)} technical resumes using natural language processing and AI analysis.

**Subjects:**
{candidates_list}

**Methodology:** LLM-based parsing, embedding similarity, and comparative analysis.

---

"""
        return header
    
    def _create_executive_summary(self, comparison_data: Dict, candidates: List[str]) -> str:
        """Create executive summary section"""
        
        llm_analysis = comparison_data.get('llm_analysis', {})
        summary = llm_analysis.get('summary', {})
        
        exec_summary = f"""## Executive Summary

### Key Findings:

1. **Experience Leadership**: {summary.get('most_experienced', 'Not specified')} demonstrates the highest experience level.

2. **Skill Diversity**: {summary.get('most_diverse_skills', 'Not specified')} shows the most varied technical skill set.

3. **Unique Contributions**: Each candidate brings distinct strengths that could benefit different organizational needs.

### Quick Statistics:
- Overall similarity score: {comparison_data.get('similarity_analysis', {}).get('average_similarity', 0):.1%}
- Common technologies identified: {len(llm_analysis.get('tech_stack_comparison', {}).get('common_technologies', []))}
- Total unique skills across candidates: {self._count_total_unique_skills(comparison_data)}

---

"""
        return exec_summary
    
    def _count_total_unique_skills(self, comparison_data: Dict) -> int:
        """Count total unique skills across all candidates"""
        tech_comp = comparison_data.get('llm_analysis', {}).get('tech_stack_comparison', {})
        all_tech = set()
        
        # Add common technologies
        all_tech.update(tech_comp.get('common_technologies', []))
        
        # Add unique technologies
        unique_by_candidate = tech_comp.get('unique_technologies_by_candidate', {})
        for candidate_tech in unique_by_candidate.values():
            all_tech.update(candidate_tech)
        
        return len(all_tech)
    
    def _create_professional_footer(self) -> str:
        """Create professional blog footer"""
        footer = """

---

### About This Analysis

**Methodology:**
- Resume parsing using advanced LLM techniques
- Embedding-based similarity analysis
- Comparative evaluation across multiple dimensions
- AI-generated insights and recommendations

**Disclaimer:**
This analysis is generated automatically and should be used as one of several inputs in the hiring process. 
Always conduct interviews and reference checks for comprehensive evaluation.

**Next Steps:**
1. Validate findings through technical interviews
2. Assess cultural fit and soft skills
3. Review portfolio and code samples
4. Conduct reference checks

*For more detailed analysis or custom evaluations, contact our technical assessment team.*

---
*Generated using AI-powered resume analysis system. Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        return footer
    
    def _create_technical_footer(self) -> str:
        """Create technical blog footer"""
        footer = """

---

### Technical Details

**Analysis Pipeline:**
1. Resume text extraction and cleaning
2. Structured information extraction using GPT-4
3. Embedding generation with Sentence Transformers
4. Similarity computation and comparative analysis
5. Insight generation and report creation

**Models Used:**
- Text parsing: Custom regex + LLM extraction
- Embeddings: all-MiniLM-L6-v2
- Analysis: GPT-4 with custom prompts
- Similarity: Cosine similarity on document embeddings

**Limitations:**
- Analysis based solely on resume content
- Does not assess actual coding ability
- May miss context from employment gaps
- No evaluation of soft skills or cultural fit

---
*System Version: 1.0 | Analysis completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        return footer
    
    def save_blog_post(self, blog_content: str, output_dir: str = "outputs/blog_posts", 
                      format: str = "markdown") -> Dict[str, str]:
        """Save blog post in multiple formats"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as markdown
        md_path = os.path.join(output_dir, f"resume_comparison_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        
        # Convert to HTML if requested
        html_path = None
        if format == "html" or format == "both":
            html_path = os.path.join(output_dir, f"resume_comparison_{timestamp}.html")
            html_content = markdown.markdown(blog_content, extensions=['extra'])
            
            # Add basic HTML styling
            styled_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Comparison Analysis</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; }}
        h2 {{ color: #555; }}
        h3 {{ color: #777; }}
        .summary {{ background: #f9f9f9; padding: 20px; border-left: 4px solid #007bff; }}
        .recommendation {{ background: #e7f3ff; padding: 15px; margin: 10px 0; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(styled_html)
        
        print(f"✓ Blog post saved as markdown: {md_path}")
        if html_path:
            print(f"✓ Blog post saved as HTML: {html_path}")
        
        return {
            "markdown": md_path,
            "html": html_path
        }
    
    def generate_complete_report(self, comparison_data: Dict, resumes_data: List[Dict], 
                               output_dir: str = "outputs") -> Dict[str, str]:
        """Generate complete report with blog and all outputs"""
        
        # Generate blog post
        blog_content = self.generate_blog_post(comparison_data, resumes_data, "professional")
        
        # Save blog post
        blog_paths = self.save_blog_post(blog_content, os.path.join(output_dir, "blog_posts"), "both")
        
        # Create additional visualizations (simplified)
        self._generate_visualizations(comparison_data, output_dir)
        
        # Create readme file
        readme_path = self._generate_readme(comparison_data, resumes_data, output_dir)
        
        return {
            "blog_markdown": blog_paths["markdown"],
            "blog_html": blog_paths["html"],
            "readme": readme_path,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_visualizations(self, comparison_data: Dict, output_dir: str):
        """Generate simple visualizations (text-based)"""
        import pandas as pd
        
        vis_dir = os.path.join(output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # Create tech stack comparison CSV
        tech_comp = comparison_data.get('llm_analysis', {}).get('tech_stack_comparison', {})
        
        # Create a simple comparison table
        candidates = comparison_data.get('candidate_names', ['Candidate 1', 'Candidate 2', 'Candidate 3'])
        
        # Tech presence matrix
        all_tech = set()
        for candidate in ['candidate1', 'candidate2', 'candidate3']:
            tech = tech_comp.get('technologies_by_candidate', {}).get(candidate, [])
            all_tech.update(tech)
        
        # Create DataFrame
        data = []
        for tech in sorted(all_tech):
            row = {'Technology': tech}
            for i, candidate in enumerate(['candidate1', 'candidate2', 'candidate3']):
                candidate_tech = tech_comp.get('technologies_by_candidate', {}).get(candidate, [])
                row[candidates[i]] = '✓' if tech in candidate_tech else ''
            data.append(row)
        
        df = pd.DataFrame(data)
        csv_path = os.path.join(vis_dir, "tech_stack_comparison.csv")
        df.to_csv(csv_path, index=False)
        
        print(f"✓ Visualization data saved: {csv_path}")
    
    def _generate_readme(self, comparison_data: Dict, resumes_data: List[Dict], output_dir: str) -> str:
        """Generate a README file for the analysis"""
        
        readme_path = os.path.join(output_dir, "ANALYSIS_README.md")
        
        candidates = comparison_data.get('candidate_names', ['Candidate 1', 'Candidate 2', 'Candidate 3'])
        
        readme_content = f"""# Resume Analysis Report

## Analysis Summary

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Candidates Analyzed:** {len(resumes_data)}

### Key Metrics
- Overall Similarity: {comparison_data.get('similarity_analysis', {}).get('average_similarity', 0):.1%}
- Common Technologies: {len(comparison_data.get('llm_analysis', {}).get('tech_stack_comparison', {}).get('common_technologies', []))}
- Total Analysis Time: Generated in minutes

### Files Generated

1. **Blog Post** (`blog_posts/`):
   - Comprehensive analysis in markdown format
   - HTML version for easy viewing

2. **Comparison Data** (`comparisons/`):
   - Detailed JSON comparison
   - Text summary

3. **Parsed Resumes** (`data/parsed/`):
   - Structured JSON for each resume

4. **Visualizations** (`visualizations/`):
   - Tech stack comparison CSV

### How to Use This Analysis

1. **Review the Blog Post** for narrative insights
2. **Examine Comparison Data** for detailed metrics
3. **Check Visualizations** for quick comparisons
4. **Use Recommendations** for hiring decisions

### Methodology

This analysis uses:
- LLM-based information extraction
- Embedding similarity calculations
- Comparative analysis algorithms
- AI-generated insights

### Notes

- All candidate names and personal details are handled confidentially
- Analysis is based solely on provided resume content
- Always supplement with interviews and references

---
*Generated by Resume Analysis System v1.0*
"""
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        return readme_path