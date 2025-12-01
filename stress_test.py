#!/usr/bin/env python3
"""
Stress Test Tool for JoveHeal Chatbot
Run with: python stress_test.py --queries queries.txt --concurrent 10
"""

import argparse
import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict


class StressTestRunner:
    def __init__(self, base_url: str, queries_file: str, concurrent: int = 10, delay: float = 0.1):
        self.base_url = base_url.rstrip('/')
        self.queries_file = queries_file
        self.concurrent = concurrent
        self.delay = delay
        self.results = []
        self.errors = []
        
    def load_queries(self) -> list:
        """Load queries from file (one per line or CSV)."""
        queries = []
        file_path = Path(self.queries_file)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Queries file not found: {self.queries_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if ',' in line and line.count(',') >= 1:
                        parts = line.split(',', 1)
                        query = parts[1].strip().strip('"\'')
                    else:
                        query = line
                    if query:
                        queries.append(query)
        
        return queries
    
    async def send_query(self, session: aiohttp.ClientSession, query: str, query_id: int) -> dict:
        """Send a single query and measure response."""
        start_time = time.time()
        result = {
            'query_id': query_id,
            'query': query[:100] + '...' if len(query) > 100 else query,
            'success': False,
            'response_time': 0,
            'status_code': None,
            'safety_triggered': False,
            'error': None,
            'response_preview': None
        }
        
        try:
            payload = {
                'message': query,
                'session_id': f'stress_test_{query_id}'
            }
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result['status_code'] = response.status
                result['response_time'] = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    result['success'] = True
                    result['safety_triggered'] = data.get('safety_triggered', False)
                    resp_text = data.get('response', '')
                    result['response_preview'] = resp_text[:100] + '...' if len(resp_text) > 100 else resp_text
                else:
                    result['error'] = f"HTTP {response.status}"
                    
        except asyncio.TimeoutError:
            result['response_time'] = time.time() - start_time
            result['error'] = "Timeout (60s)"
        except Exception as e:
            result['response_time'] = time.time() - start_time
            result['error'] = str(e)
        
        return result
    
    async def run_batch(self, session: aiohttp.ClientSession, queries: list, start_id: int) -> list:
        """Run a batch of queries concurrently."""
        tasks = []
        for i, query in enumerate(queries):
            tasks.append(self.send_query(session, query, start_id + i))
            await asyncio.sleep(self.delay)
        
        return await asyncio.gather(*tasks)
    
    async def run_test(self) -> dict:
        """Run the full stress test."""
        queries = self.load_queries()
        total_queries = len(queries)
        
        print(f"Loaded {total_queries} queries from {self.queries_file}")
        print(f"Running with {self.concurrent} concurrent requests, {self.delay}s delay")
        print("-" * 50)
        
        start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=self.concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            for i in range(0, total_queries, self.concurrent):
                batch = queries[i:i + self.concurrent]
                batch_results = await self.run_batch(session, batch, i)
                self.results.extend(batch_results)
                
                completed = min(i + self.concurrent, total_queries)
                success_count = sum(1 for r in self.results if r['success'])
                print(f"Progress: {completed}/{total_queries} ({success_count} successful)")
        
        total_time = time.time() - start_time
        
        return self.generate_report(total_time)
    
    def generate_report(self, total_time: float) -> dict:
        """Generate test report statistics."""
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        safety_triggered = [r for r in successful if r['safety_triggered']]
        
        response_times = [r['response_time'] for r in successful]
        
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'queries_file': self.queries_file,
                'concurrent_requests': self.concurrent,
                'delay_between_requests': self.delay,
                'total_test_time': round(total_time, 2)
            },
            'summary': {
                'total_queries': len(self.results),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': round(len(successful) / len(self.results) * 100, 2) if self.results else 0,
                'safety_triggered': len(safety_triggered),
                'safety_trigger_rate': round(len(safety_triggered) / len(successful) * 100, 2) if successful else 0
            },
            'response_times': {
                'avg': round(statistics.mean(response_times), 3) if response_times else 0,
                'min': round(min(response_times), 3) if response_times else 0,
                'max': round(max(response_times), 3) if response_times else 0,
                'median': round(statistics.median(response_times), 3) if response_times else 0,
                'std_dev': round(statistics.stdev(response_times), 3) if len(response_times) > 1 else 0
            },
            'throughput': {
                'queries_per_second': round(len(self.results) / total_time, 2) if total_time > 0 else 0,
                'successful_per_second': round(len(successful) / total_time, 2) if total_time > 0 else 0
            },
            'errors': defaultdict(int),
            'sample_responses': [],
            'failed_queries': []
        }
        
        for r in failed:
            error_type = r.get('error', 'Unknown')
            report['errors'][error_type] += 1
        
        report['errors'] = dict(report['errors'])
        
        for r in successful[:5]:
            report['sample_responses'].append({
                'query': r['query'],
                'response_time': r['response_time'],
                'safety_triggered': r['safety_triggered'],
                'response_preview': r['response_preview']
            })
        
        for r in failed[:10]:
            report['failed_queries'].append({
                'query': r['query'],
                'error': r['error'],
                'status_code': r['status_code']
            })
        
        return report
    
    def save_markdown_report(self, report: dict, output_file: str = 'stress_test_report.md'):
        """Save report as markdown file."""
        md = []
        md.append("# JoveHeal Chatbot Stress Test Report\n")
        
        md.append("## Test Configuration\n")
        md.append(f"- **Timestamp:** {report['test_info']['timestamp']}")
        md.append(f"- **Queries File:** {report['test_info']['queries_file']}")
        md.append(f"- **Concurrent Requests:** {report['test_info']['concurrent_requests']}")
        md.append(f"- **Delay Between Requests:** {report['test_info']['delay_between_requests']}s")
        md.append(f"- **Total Test Duration:** {report['test_info']['total_test_time']}s\n")
        
        md.append("## Summary\n")
        md.append("| Metric | Value |")
        md.append("|--------|-------|")
        md.append(f"| Total Queries | {report['summary']['total_queries']} |")
        md.append(f"| Successful | {report['summary']['successful']} |")
        md.append(f"| Failed | {report['summary']['failed']} |")
        md.append(f"| Success Rate | {report['summary']['success_rate']}% |")
        md.append(f"| Safety Triggered | {report['summary']['safety_triggered']} |")
        md.append(f"| Safety Trigger Rate | {report['summary']['safety_trigger_rate']}% |\n")
        
        md.append("## Response Times\n")
        md.append("| Metric | Value (seconds) |")
        md.append("|--------|-----------------|")
        md.append(f"| Average | {report['response_times']['avg']} |")
        md.append(f"| Minimum | {report['response_times']['min']} |")
        md.append(f"| Maximum | {report['response_times']['max']} |")
        md.append(f"| Median | {report['response_times']['median']} |")
        md.append(f"| Std Deviation | {report['response_times']['std_dev']} |\n")
        
        md.append("## Throughput\n")
        md.append(f"- **Queries/second:** {report['throughput']['queries_per_second']}")
        md.append(f"- **Successful queries/second:** {report['throughput']['successful_per_second']}\n")
        
        if report['errors']:
            md.append("## Errors\n")
            md.append("| Error Type | Count |")
            md.append("|------------|-------|")
            for error, count in report['errors'].items():
                md.append(f"| {error} | {count} |")
            md.append("")
        
        if report['sample_responses']:
            md.append("## Sample Successful Responses\n")
            for i, sample in enumerate(report['sample_responses'], 1):
                md.append(f"### Query {i}")
                md.append(f"- **Query:** {sample['query']}")
                md.append(f"- **Response Time:** {sample['response_time']:.3f}s")
                md.append(f"- **Safety Triggered:** {sample['safety_triggered']}")
                md.append(f"- **Response:** {sample['response_preview']}\n")
        
        if report['failed_queries']:
            md.append("## Failed Queries (First 10)\n")
            md.append("| Query | Error | Status |")
            md.append("|-------|-------|--------|")
            for fq in report['failed_queries']:
                query = fq['query'].replace('|', '\\|')
                md.append(f"| {query} | {fq['error']} | {fq['status_code']} |")
            md.append("")
        
        md.append("---\n")
        md.append("*Report generated by JoveHeal Stress Test Tool*\n")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
        
        print(f"\nReport saved to: {output_file}")
        return output_file


async def main():
    parser = argparse.ArgumentParser(description='Stress test JoveHeal Chatbot')
    parser.add_argument('--queries', '-q', required=True, help='Path to queries file (one per line)')
    parser.add_argument('--url', '-u', default='http://localhost:8080', help='Base URL of webhook server')
    parser.add_argument('--concurrent', '-c', type=int, default=10, help='Number of concurrent requests')
    parser.add_argument('--delay', '-d', type=float, default=0.1, help='Delay between requests (seconds)')
    parser.add_argument('--output', '-o', default='stress_test_report.md', help='Output markdown file')
    
    args = parser.parse_args()
    
    runner = StressTestRunner(
        base_url=args.url,
        queries_file=args.queries,
        concurrent=args.concurrent,
        delay=args.delay
    )
    
    report = await runner.run_test()
    
    print("\n" + "=" * 50)
    print("STRESS TEST COMPLETE")
    print("=" * 50)
    print(f"Total Queries: {report['summary']['total_queries']}")
    print(f"Success Rate: {report['summary']['success_rate']}%")
    print(f"Avg Response Time: {report['response_times']['avg']}s")
    print(f"Throughput: {report['throughput']['queries_per_second']} queries/sec")
    
    runner.save_markdown_report(report, args.output)
    
    with open(args.output.replace('.md', '.json'), 'w') as f:
        json.dump(report, f, indent=2)
    print(f"JSON report saved to: {args.output.replace('.md', '.json')}")


if __name__ == '__main__':
    asyncio.run(main())
