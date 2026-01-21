#!/usr/bin/env python3
"""
Main script for Resume Analysis & Comparison System
Execute: python main.py --resumes resume1.pdf resume2.pdf resume3.pdf
"""

import os
import sys
import argparse
from datetime import datetime
from src.tools.tool1_resume_parser import ResumeParser
from src.tools.tool2_comparison_engine import ComparisonEngine
from src.tools.tool3_blog_generator import BlogGenerator
from src.utils.file_handlers import FileHandler

def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(description="Resume Analysis & Comparison System")
    parser.add_argument('--resumes', nargs='+', required=True, 
                       help='Paths to resume files (PDF/DOC/TXT)')
    parser.add_argument('--output-dir', default='outputs',
                       help='Output directory for results')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--generate-blog', action='store_true', default=True,
                       help='Generate blog post (default: True)')
    parser.add_argument('--questions', nargs='+',
                       default=['What are the tech stacks?',
                                'How many years of experience?',
                                'What are the strongest skills?'],
                       help='Questions to answer about each resume')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RESUME ANALYSIS & COMPARISON SYSTEM")
    print("=" * 60)
    print(f"Starting analysis at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Resumes to analyze: {len(args.resumes)}")
    print()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # TOOL 1: Parse Resumes
        print("🔧 STEP 1: Parsing resumes...")
        print("-" * 40)
        
        parser_tool = ResumeParser(args.config)
        resumes_data = parser_tool.process_multiple_resumes(args.resumes)
        
        # Answer questions for each resume
        for i, resume in enumerate(resumes_data):
            print(f"\n📋 Candidate {i+1}: {resume.get('name', 'Unknown')}")
            answers = parser_tool.answer_questions(resume, args.questions)
            for question, answer in answers.items():
                print(f"   Q: {question}")
                print(f"   A: {answer[:100]}..." if len(answer) > 100 else f"   A: {answer}")
        
        print(f"\n✅ Parsed {len(resumes_data)} resumes successfully")
        
        # TOOL 2: Compare Resumes
        print("\n🔧 STEP 2: Comparing resumes...")
        print("-" * 40)
        
        comparison_tool = ComparisonEngine(args.config)
        comparison_data = comparison_tool.compare_resumes(resumes_data)
        
        # Save comparison report
        comparison_path = os.path.join(args.output_dir, "comparisons", "full_comparison.json")
        comparison_tool.generate_comparison_report(comparison_data, comparison_path)
        
        print(f"✅ Comparison completed and saved to {comparison_path}")
        
        # TOOL 3: Generate Blog Post
        if args.generate_blog:
            print("\n🔧 STEP 3: Generating blog post...")
            print("-" * 40)
            
            blog_tool = BlogGenerator(args.config)
            blog_paths = blog_tool.generate_complete_report(
                comparison_data, resumes_data, args.output_dir
            )
            
            print(f"✅ Blog post generated:")
            print(f"   • Markdown: {blog_paths['blog_markdown']}")
            if blog_paths.get('blog_html'):
                print(f"   • HTML: {blog_paths['blog_html']}")
            print(f"   • README: {blog_paths['readme']}")
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ ANALYSIS COMPLETE!")
        print("=" * 60)
        
        candidates = [resume.get('name', f'Candidate {i+1}') for i, resume in enumerate(resumes_data)]
        print(f"\n📊 Summary for: {', '.join(candidates)}")
        
        # Display key insights
        llm_analysis = comparison_data.get('llm_analysis', {})
        summary = llm_analysis.get('summary', {})
        
        print(f"\n🎯 Key Insights:")
        print(f"   • Most Experienced: {summary.get('most_experienced', 'N/A')}")
        print(f"   • Most Diverse Skills: {summary.get('most_diverse_skills', 'N/A')}")
        
        tech_comp = llm_analysis.get('tech_stack_comparison', {})
        common_tech = tech_comp.get('common_technologies', [])
        print(f"   • Common Technologies: {len(common_tech)} shared skills")
        
        sim_score = comparison_data.get('similarity_analysis', {}).get('average_similarity', 0)
        print(f"   • Overall Similarity: {sim_score:.1%}")
        
        print(f"\n📁 Output files saved in: {args.output_dir}/")
        print(f"\n⏱️  Total time: Analysis completed at {datetime.now().strftime('%H:%M:%S')}")
        
        # Save final summary
        final_summary = {
            "timestamp": datetime.now().isoformat(),
            "candidates_analyzed": candidates,
            "output_files": {
                "parsed_resumes": f"{args.output_dir}/data/parsed/",
                "comparison": comparison_path,
                "blog": blog_paths.get('blog_markdown', '') if args.generate_blog else None
            },
            "key_metrics": {
                "total_candidates": len(resumes_data),
                "common_technologies_count": len(common_tech),
                "average_similarity": sim_score
            }
        }
        
        summary_path = os.path.join(args.output_dir, "analysis_summary.json")
        FileHandler.save_json(final_summary, summary_path)
        print(f"\n📄 Final summary saved to: {summary_path}")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()