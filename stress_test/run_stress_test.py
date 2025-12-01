import re
import time
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot_engine import generate_response, is_openai_available

def parse_questions_by_section(md_file_path):
    """Parse the MD file and group questions by section."""
    with open(md_file_path, 'r') as f:
        content = f.read()
    
    sections = {}
    current_section = None
    current_questions = []
    
    lines = content.split('\n')
    for line in lines:
        if line.startswith('## '):
            if current_section and current_questions:
                sections[current_section] = current_questions
            current_section = line.replace('## ', '').strip()
            current_questions = []
        elif re.match(r'^\d+\.', line.strip()):
            question = re.sub(r'^\d+\.\s*', '', line.strip()).strip()
            if question:
                current_questions.append(question)
    
    if current_section and current_questions:
        sections[current_section] = current_questions
    
    return sections

def run_section_test(section_name, questions, output_dir):
    """Run all questions in a section conversationally and save results."""
    results = []
    conversation_history = []
    total_time = 0
    
    print(f"\n{'='*60}")
    print(f"Section: {section_name}")
    print(f"Questions: {len(questions)}")
    print('='*60)
    
    for i, question in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] Processing: {question[:50]}...")
        
        start_time = time.time()
        response = generate_response(question, conversation_history)
        end_time = time.time()
        
        response_time = round(end_time - start_time, 2)
        total_time += response_time
        
        answer = response.get('response', 'No response')
        sources = response.get('sources', [])
        is_safe = not response.get('safety_triggered', False)
        error = response.get('error', None)
        
        conversation_history.append({
            "role": "user",
            "content": question
        })
        conversation_history.append({
            "role": "assistant",
            "content": answer
        })
        
        result = {
            "question_number": i,
            "question": question,
            "answer": answer,
            "metrics": {
                "response_time_seconds": response_time,
                "sources_used": sources,
                "source_count": len(sources),
                "is_safe_response": is_safe,
                "error": error
            }
        }
        results.append(result)
        
        print(f"      Response time: {response_time}s | Sources: {len(sources)}")
    
    section_filename = section_name.replace(' ', '_').replace('/', '_').replace('&', 'and')
    section_filename = re.sub(r'[^\w\s-]', '', section_filename).strip()
    output_file = f"{output_dir}/section_{section_filename}.md"
    
    with open(output_file, 'w') as f:
        f.write(f"# Stress Test Results: {section_name}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Questions:** {len(questions)}\n")
        f.write(f"**Total Response Time:** {round(total_time, 2)} seconds\n")
        f.write(f"**Average Response Time:** {round(total_time/len(questions), 2)} seconds\n")
        f.write(f"**Conversation Mode:** Conversational (context preserved)\n\n")
        f.write("---\n\n")
        
        for result in results:
            f.write(f"## Q{result['question_number']}: {result['question']}\n\n")
            f.write(f"**Answer:**\n\n{result['answer']}\n\n")
            f.write(f"**Metrics:**\n")
            f.write(f"- Response Time: {result['metrics']['response_time_seconds']} seconds\n")
            f.write(f"- Sources Used: {result['metrics']['source_count']}\n")
            if result['metrics']['sources_used']:
                for src in result['metrics']['sources_used']:
                    f.write(f"  - {src}\n")
            f.write(f"- Safe Response: {'Yes' if result['metrics']['is_safe_response'] else 'No'}\n")
            if result['metrics']['error']:
                f.write(f"- Error: {result['metrics']['error']}\n")
            f.write("\n---\n\n")
    
    print(f"  Saved to: {output_file}")
    return {
        "section": section_name,
        "questions_count": len(questions),
        "total_time": round(total_time, 2),
        "avg_time": round(total_time/len(questions), 2),
        "output_file": output_file
    }

def run_stress_test():
    """Main stress test runner."""
    print("\n" + "="*60)
    print("JOVEHEAL CHATBOT STRESS TEST")
    print("="*60)
    
    if not is_openai_available():
        print("ERROR: OpenAI is not configured. Cannot run stress test.")
        return
    
    md_file = "stress_test/stress_test_md/120_questions_batch1.md"
    output_dir = "stress_test/stress_test_md_output"
    
    print(f"\nParsing questions from: {md_file}")
    sections = parse_questions_by_section(md_file)
    
    total_questions = sum(len(q) for q in sections.values())
    print(f"Found {len(sections)} sections with {total_questions} total questions\n")
    
    for section_name, questions in sections.items():
        print(f"  - {section_name}: {len(questions)} questions")
    
    summary = []
    overall_start = time.time()
    
    for section_name, questions in sections.items():
        result = run_section_test(section_name, questions, output_dir)
        summary.append(result)
    
    overall_time = round(time.time() - overall_start, 2)
    
    summary_file = f"{output_dir}/00_SUMMARY.md"
    with open(summary_file, 'w') as f:
        f.write("# Stress Test Summary\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Questions:** {total_questions}\n")
        f.write(f"**Total Sections:** {len(sections)}\n")
        f.write(f"**Total Execution Time:** {overall_time} seconds\n")
        f.write(f"**Overall Average Response Time:** {round(overall_time/total_questions, 2)} seconds\n\n")
        f.write("## Section Results\n\n")
        f.write("| Section | Questions | Total Time | Avg Time | Output File |\n")
        f.write("|---------|-----------|------------|----------|-------------|\n")
        for s in summary:
            f.write(f"| {s['section'][:30]}... | {s['questions_count']} | {s['total_time']}s | {s['avg_time']}s | {s['output_file'].split('/')[-1]} |\n")
    
    print("\n" + "="*60)
    print("STRESS TEST COMPLETE")
    print("="*60)
    print(f"Total time: {overall_time} seconds")
    print(f"Summary saved to: {summary_file}")
    print("="*60)

if __name__ == "__main__":
    run_stress_test()
