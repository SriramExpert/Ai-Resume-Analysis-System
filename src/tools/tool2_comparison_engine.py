import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.utils.file_handlers import FileHandler
from src.llm_integration.llm_handler import LLMHandler

class ComparisonEngine:
    """Tool 2: Compare and analyze multiple resumes"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = FileHandler.load_config(config_path)
        self.embedding_generator = EmbeddingGenerator()
        self.llm_handler = LLMHandler(config_path)
        self.file_handler = FileHandler()
    
    def compare_resumes(self, resumes_data: List[Dict]) -> Dict[str, Any]:
        """Main comparison function"""
        
        # Generate embeddings for all resumes
        embeddings_list = []
        for resume in resumes_data:
            embeddings = self.embedding_generator.generate_section_embeddings(resume)
            embeddings_list.append(embeddings)
        
        # Compute similarity matrix
        similarity_matrix = self.embedding_generator.compute_similarity_matrix(embeddings_list)
        
        # Get LLM-based comparison
        llm_comparison = self.llm_handler.compare_resumes(resumes_data)
        
        # Generate detailed comparison metrics
        detailed_comparison = self._generate_detailed_comparison(resumes_data, similarity_matrix)
        
        # Combine all comparisons
        final_comparison = {
            "llm_analysis": llm_comparison,
            "similarity_analysis": {
                "overall_similarity_matrix": similarity_matrix.tolist(),
                "average_similarity": float(np.mean(similarity_matrix)),
                "most_similar_pair": self._find_most_similar_pair(similarity_matrix),
                "least_similar_pair": self._find_least_similar_pair(similarity_matrix)
            },
            "detailed_metrics": detailed_comparison,
            "candidate_names": [resume.get('name', f'Candidate {i+1}') for i, resume in enumerate(resumes_data)]
        }
        
        return final_comparison
    
    def _generate_detailed_comparison(self, resumes_data: List[Dict], similarity_matrix: np.ndarray) -> Dict:
        """Generate detailed comparison metrics"""
        
        comparison = {
            "tech_stack_analysis": self._compare_tech_stacks(resumes_data),
            "experience_analysis": self._compare_experience(resumes_data),
            "skills_analysis": self._compare_skills(resumes_data),
            "education_analysis": self._compare_education(resumes_data)
        }
        
        # Add similarity scores
        comparison["similarity_scores"] = {
            "tech_stack_similarity": self._calculate_tech_similarity(resumes_data),
            "experience_similarity": self._calculate_experience_similarity(resumes_data)
        }
        
        return comparison
    
    def _compare_tech_stacks(self, resumes_data: List[Dict]) -> Dict:
        """Compare technology stacks"""
        all_tech = []
        tech_by_candidate = {}
        
        for i, resume in enumerate(resumes_data):
            tech_stack = set(resume.get('tech_stack', []))
            all_tech.extend(tech_stack)
            tech_by_candidate[f"candidate_{i+1}"] = list(tech_stack)
        
        # Find common and unique technologies
        tech_sets = [set(resume.get('tech_stack', [])) for resume in resumes_data]
        
        common_tech = set.intersection(*tech_sets) if tech_sets else set()
        all_unique_tech = set.union(*tech_sets) if tech_sets else set()
        unique_by_candidate = {}
        
        for i, tech_set in enumerate(tech_sets):
            other_sets = tech_sets[:i] + tech_sets[i+1:]
            if other_sets:
                other_union = set.union(*other_sets)
                unique_by_candidate[f"candidate_{i+1}"] = list(tech_set - other_union)
            else:
                unique_by_candidate[f"candidate_{i+1}"] = list(tech_set)
        
        return {
            "common_technologies": list(common_tech),
            "all_technologies": list(all_unique_tech),
            "technologies_by_candidate": tech_by_candidate,
            "unique_technologies_by_candidate": unique_by_candidate,
            "technology_counts": {f"candidate_{i+1}": len(tech) for i, tech in enumerate(tech_sets)}
        }
    
    def _compare_experience(self, resumes_data: List[Dict]) -> Dict:
        """Compare experience levels and types"""
        
        experience_data = []
        for resume in resumes_data:
            exp_years = resume.get('calculated_metrics', {}).get('total_experience_years', 0)
            experience_data.append({
                "years": exp_years,
                "roles": [exp.get('title', '') for exp in resume.get('experience', [])],
                "companies": [exp.get('company', '') for exp in resume.get('experience', [])],
                "role_count": len(resume.get('experience', []))
            })
        
        # Find common industries/roles (simplified)
        all_roles = []
        for data in experience_data:
            all_roles.extend(data["roles"])
        
        from collections import Counter
        role_counts = Counter(all_roles)
        common_roles = [role for role, count in role_counts.items() if count > 1]
        
        return {
            "experience_years": [data["years"] for data in experience_data],
            "average_experience": np.mean([data["years"] for data in experience_data]),
            "experience_range": {
                "min": min([data["years"] for data in experience_data]),
                "max": max([data["years"] for data in experience_data])
            },
            "common_roles": common_roles,
            "role_diversity": [len(set(data["roles"])) for data in experience_data],
            "company_count": [len(set(data["companies"])) for data in experience_data]
        }
    
    def _compare_skills(self, resumes_data: List[Dict]) -> Dict:
        """Compare skills across candidates"""
        
        skill_categories = ['programming_languages', 'frameworks', 'tools', 
                           'databases', 'cloud_services', 'certifications']
        
        comparison = {}
        for category in skill_categories:
            category_skills = []
            for resume in resumes_data:
                skills = resume.get('skills', {}).get(category, [])
                category_skills.append(set(skills))
            
            if category_skills:
                common = set.intersection(*category_skills) if len(category_skills) > 1 else set()
                all_skills = set.union(*category_skills) if category_skills else set()
                
                comparison[category] = {
                    "common": list(common),
                    "all": list(all_skills),
                    "counts": [len(skills) for skills in category_skills]
                }
        
        return comparison
    
    def _compare_education(self, resumes_data: List[Dict]) -> Dict:
        """Compare educational background"""
        
        education_levels = []
        institutions = []
        degrees = []
        
        for resume in resumes_data:
            for edu in resume.get('education', []):
                degree = edu.get('degree', '').lower()
                institution = edu.get('institution', '')
                
                degrees.append(degree)
                institutions.append(institution)
                
                # Categorize education level
                if any(term in degree for term in ['phd', 'doctor']):
                    education_levels.append('phd')
                elif any(term in degree for term in ['master', 'ms', 'm.']):
                    education_levels.append('masters')
                elif any(term in degree for term in ['bachelor', 'bs', 'ba', 'b.']):
                    education_levels.append('bachelors')
                else:
                    education_levels.append('other')
        
        from collections import Counter
        return {
            "degree_levels": dict(Counter(education_levels)),
            "unique_institutions": len(set(institutions)),
            "common_degrees": [deg for deg, count in Counter(degrees).items() if count > 1]
        }
    
    def _calculate_tech_similarity(self, resumes_data: List[Dict]) -> List[List[float]]:
        """Calculate Jaccard similarity for tech stacks"""
        tech_sets = [set(resume.get('tech_stack', [])) for resume in resumes_data]
        
        similarity_matrix = []
        for i in range(len(tech_sets)):
            row = []
            for j in range(len(tech_sets)):
                if i == j:
                    row.append(1.0)
                else:
                    set1 = tech_sets[i]
                    set2 = tech_sets[j]
                    if not set1 and not set2:
                        similarity = 1.0
                    elif not set1 or not set2:
                        similarity = 0.0
                    else:
                        similarity = len(set1 & set2) / len(set1 | set2)
                    row.append(similarity)
            similarity_matrix.append(row)
        
        return similarity_matrix
    
    def _calculate_experience_similarity(self, resumes_data: List[Dict]) -> List[List[float]]:
        """Calculate experience similarity based on role titles and descriptions using FastEmbed"""
        # Collect all role descriptions
        exp_embeddings = []
        for resume in resumes_data:
            # Generate or retrieve experience embedding
            embeddings = self.embedding_generator.generate_section_embeddings(resume)
            if 'experience' in embeddings:
                exp_embeddings.append(embeddings['experience'])
            else:
                # Fallback to full document if no specific experience found
                exp_embeddings.append(embeddings['full_document'])
        
        if len(exp_embeddings) > 1:
            similarity = cosine_similarity(exp_embeddings)
            return similarity.tolist()
        
        return [[1.0 if i == j else 0.0 for j in range(len(resumes_data))] 
                for i in range(len(resumes_data))]
    
    def _find_most_similar_pair(self, similarity_matrix: np.ndarray) -> Dict:
        """Find the most similar pair of candidates"""
        n = len(similarity_matrix)
        max_sim = -1
        pair = (0, 0)
        
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] > max_sim:
                    max_sim = similarity_matrix[i][j]
                    pair = (i, j)
        
        return {
            "candidate_indices": pair,
            "similarity_score": float(max_sim)
        }
    
    def _find_least_similar_pair(self, similarity_matrix: np.ndarray) -> Dict:
        """Find the least similar pair of candidates"""
        n = len(similarity_matrix)
        min_sim = 2  # Start higher than possible max
        pair = (0, 0)
        
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] < min_sim:
                    min_sim = similarity_matrix[i][j]
                    pair = (i, j)
        
        return {
            "candidate_indices": pair,
            "similarity_score": float(min_sim)
        }
    
    def generate_comparison_report(self, comparison_data: Dict, output_path: str = None):
        """Generate a comprehensive comparison report"""
        
        if output_path is None:
            output_path = "outputs/comparisons/comparison_report.json"
        
        # Save the comparison data
        self.file_handler.save_json(comparison_data, output_path)
        
        # Also create a summary text file
        summary_path = output_path.replace('.json', '_summary.txt')
        summary = self._create_summary_text(comparison_data)
        
        with open(summary_path, 'w') as f:
            f.write(summary)
        
        print(f"Comparison report saved to: {output_path}")
        print(f"Summary saved to: {summary_path}")
        
        return output_path
    
    def _create_summary_text(self, comparison_data: Dict) -> str:
        """Create a text summary of the comparison"""
        
        candidates = comparison_data.get('candidate_names', ['Candidate 1', 'Candidate 2', 'Candidate 3'])
        llm_analysis = comparison_data.get('llm_analysis', {})
        sim_analysis = comparison_data.get('similarity_analysis', {})
        
        summary = f"RESUME COMPARISON SUMMARY\n"
        summary += "=" * 50 + "\n\n"
        
        summary += f"Candidates: {', '.join(candidates)}\n\n"
        
        # Overall similarity
        avg_sim = sim_analysis.get('average_similarity', 0)
        summary += f"Overall Similarity Score: {avg_sim:.2%}\n\n"
        
        # Most experienced
        most_exp = llm_analysis.get('summary', {}).get('most_experienced', 'N/A')
        summary += f"Most Experienced: {most_exp}\n"
        
        # Most diverse skills
        most_diverse = llm_analysis.get('summary', {}).get('most_diverse_skills', 'N/A')
        summary += f"Most Diverse Skills: {most_diverse}\n\n"
        
        # Tech stack comparison
        tech_comp = llm_analysis.get('tech_stack_comparison', {})
        common_tech = tech_comp.get('common_technologies', [])
        if common_tech:
            summary += f"Common Technologies ({len(common_tech)}):\n"
            for tech in common_tech[:10]:  # Limit to top 10
                summary += f"  • {tech}\n"
            if len(common_tech) > 10:
                summary += f"  ... and {len(common_tech) - 10} more\n"
        summary += "\n"
        
        # Recommendations
        recs = llm_analysis.get('recommendations', {})
        summary += "ROLE RECOMMENDATIONS:\n"
        for role, rec in recs.items():
            summary += f"  • {role.replace('_', ' ').title()}: {rec}\n"
        
        return summary

    def calculate_performance_metrics(self, resumes_data: List[Dict]) -> List[Dict]:
        """Calculate performance scores (1-10) for candidates"""
        metrics = []
        for i, resume in enumerate(resumes_data):
            # 1. Technical Score (based on tech stack size)
            tech_count = len(resume.get('tech_stack', []))
            tech_score = min(10.0, 2.0 + (tech_count * 0.5))
            
            # 2. Experience Score (based on years)
            exp_years = 0
            # Try to get from calculated_metrics if present
            exp_years = resume.get('calculated_metrics', {}).get('total_experience_years', 0)
            if not exp_years:
                # Fallback: estimate based on experience entries
                exp_years = len(resume.get('experience', [])) * 2 
            exp_score = min(10.0, 3.0 + (exp_years * 0.4))
            
            # 3. Education Score
            edu_score = 5.0
            levels = [str(edu.get('degree', '')).lower() for edu in resume.get('education', [])]
            if any(l for l in levels if 'phd' in l or 'doctor' in l): edu_score = 10.0
            elif any(l for l in levels if 'master' in l or 'ms' in l): edu_score = 8.5
            elif any(l for l in levels if 'bachelor' in l or 'bs' in l): edu_score = 7.0
            
            # 4. Keyword Match (diversity)
            skills = resume.get('skills', {})
            skill_count = sum(len(v) for v in skills.values() if isinstance(v, list))
            diversity_score = min(10.0, 4.0 + (skill_count * 0.2))

            metrics.append({
                "name": resume.get('name', f"Candidate {i+1}"),
                "scores": {
                    "Technical": round(float(tech_score), 1),
                    "Experience": round(float(exp_score), 1),
                    "Education": round(float(edu_score), 1),
                    "Diversity": round(float(diversity_score), 1)
                },
                "overall_match": round((tech_score + exp_score + edu_score + diversity_score) / 40 * 100, 1)
            })
            
        return metrics