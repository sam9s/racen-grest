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

def run_stress_test():
    """Main stress test runner - creates ONE consolidated output file."""
    print("\n" + "="*60)
    print("JOVEHEAL CHATBOT STRESS TEST")
    print("="*60)
    
    if not is_openai_available():
        print("ERROR: OpenAI is not configured. Cannot run stress test.")
        return
    
    md_file = "stress_test/stress_test_md/120_questions_batch1.md"
    output_dir = "stress_test/stress_test_md_output"
    output_file = f"{output_dir}/batch1_full_results.md"
    
    print(f"\nParsing questions from: {md_file}")
    sections = parse_questions_by_section(md_file)
    
    total_questions = sum(len(q) for q in sections.values())
    print(f"Found {len(sections)} sections with {total_questions} total questions\n")
    
    for section_name, questions in sections.items():
        print(f"  - {section_name}: {len(questions)} questions")
    
    all_results = []
    section_summaries = []
    overall_start = time.time()
    global_question_num = 0
    
    for section_name, questions in sections.items():
        print(f"\n{'='*60}")
        print(f"Section: {section_name}")
        print(f"Questions: {len(questions)}")
        print('='*60)
        
        section_results = []
        conversation_history = []
        section_start = time.time()
        
        for i, question in enumerate(questions, 1):
            global_question_num += 1
            print(f"  [{global_question_num}/{total_questions}] Processing: {question[:50]}...")
            
            start_time = time.time()
            response = generate_response(question, conversation_history)
            end_time = time.time()
            
            response_time = round(end_time - start_time, 2)
            
            answer = response.get('response', 'No response')
            sources = response.get('sources', [])
            is_safe = not response.get('safety_triggered', False)
            error = response.get('error', None)
            
            conversation_history.append({"role": "user", "content": question})
            conversation_history.append({"role": "assistant", "content": answer})
            
            result = {
                "global_num": global_question_num,
                "section_num": i,
                "section": section_name,
                "question": question,
                "answer": answer,
                "response_time": response_time,
                "sources": sources,
                "is_safe": is_safe,
                "error": error
            }
            section_results.append(result)
            print(f"      Response time: {response_time}s | Sources: {len(sources)}")
        
        section_time = round(time.time() - section_start, 2)
        section_summaries.append({
            "section": section_name,
            "questions": len(questions),
            "total_time": section_time,
            "avg_time": round(section_time / len(questions), 2)
        })
        all_results.extend(section_results)
    
    overall_time = round(time.time() - overall_start, 2)
    
    print(f"\n\nWriting consolidated output to: {output_file}")
    
    with open(output_file, 'w') as f:
        f.write("# JoveHeal Chatbot Stress Test - Full Results (Batch 1)\n\n")
        f.write("---\n\n")
        f.write("## SUMMARY\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Questions | {total_questions} |\n")
        f.write(f"| Total Sections | {len(sections)} |\n")
        f.write(f"| Total Execution Time | {overall_time} seconds |\n")
        f.write(f"| Average Response Time | {round(overall_time/total_questions, 2)} seconds |\n")
        f.write(f"| Conversation Mode | Conversational (context preserved per section) |\n\n")
        
        f.write("### Section Breakdown\n\n")
        f.write("| Section | Questions | Total Time | Avg Time |\n")
        f.write("|---------|-----------|------------|----------|\n")
        for s in section_summaries:
            f.write(f"| {s['section']} | {s['questions']} | {s['total_time']}s | {s['avg_time']}s |\n")
        
        f.write("\n---\n\n")
        
        current_section = None
        for result in all_results:
            if result['section'] != current_section:
                current_section = result['section']
                f.write(f"## {current_section}\n\n")
            
            f.write(f"### Q{result['global_num']}: {result['question']}\n\n")
            f.write(f"**Answer:**\n\n{result['answer']}\n\n")
            f.write(f"**Metrics:**\n")
            f.write(f"- Response Time: {result['response_time']} seconds\n")
            f.write(f"- Sources Used: {len(result['sources'])}\n")
            if result['sources']:
                for src in result['sources']:
                    f.write(f"  - {src}\n")
            f.write(f"- Safe Response: {'Yes' if result['is_safe'] else 'No'}\n")
            if result['error']:
                f.write(f"- Error: {result['error']}\n")
            f.write("\n---\n\n")
    
    print("\n" + "="*60)
    print("STRESS TEST COMPLETE")
    print("="*60)
    print(f"Total time: {overall_time} seconds")
    print(f"Output saved to: {output_file}")
    print("="*60)

if __name__ == "__main__":
    run_stress_test()
