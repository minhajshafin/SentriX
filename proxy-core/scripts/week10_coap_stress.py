#!/usr/bin/env python3

"""
Week 10: CoAP Stress Test Generator
Sustained high-volume CoAP traffic for performance and detection validation
"""

import aiocoap
import asyncio
import json
import time
import argparse
from collections import defaultdict

class CoAPStressClient:
    def __init__(self, server_host='localhost', server_port=5683, num_clients=10, req_rate=10):
        """
        Args:
            server_host: CoAP server address
            server_port: CoAP server port
            num_clients: Number of concurrent CoAP clients
            req_rate: Requests per second per client
        """
        self.server_host = server_host
        self.server_port = server_port
        self.num_clients = num_clients
        self.req_rate = req_rate
        self.metrics = {
            'sent': 0,
            'success': 0,
            'failures': 0,
            'latencies': []
        }
        
    async def client_worker(self, client_id, duration_sec):
        """Async worker sending CoAP requests"""
        try:
            context = await aiocoap.Context.create_client_context()
            
            start_time = time.time()
            req_count = 0
            interval = 1.0 / self.req_rate
            
            resources = [
                f'stress/client/{client_id}/telemetry',
                f'stress/client/{client_id}/sensor/temperature',
                f'stress/client/{client_id}/sensor/humidity',
                f'stress/client/{client_id}/actuator/led'
            ]
            
            while time.time() - start_time < duration_sec:
                resource = resources[req_count % len(resources)]
                
                try:
                    uri = f'coap://{self.server_host}:{self.server_port}/{resource}'
                    request = aiocoap.Message(code=aiocoap.Code.GET, uri=uri)
                    
                    req_start = time.time()
                    response = await asyncio.wait_for(context.request(request).response, timeout=2.0)
                    latency = (time.time() - req_start) * 1000  # ms
                    
                    self.metrics['sent'] += 1
                    if response.code.is_success():
                        self.metrics['success'] += 1
                    else:
                        self.metrics['failures'] += 1
                    
                    self.metrics['latencies'].append(latency)
                    req_count += 1
                    
                except asyncio.TimeoutError:
                    self.metrics['failures'] += 1
                except Exception as e:
                    self.metrics['failures'] += 1
                    print(f"Request error (client {client_id}): {e}")
                
                await asyncio.sleep(interval)
            
            await context.shutdown()
        except Exception as e:
            print(f"Client {client_id} error: {e}")
            self.metrics['failures'] += 1
    
    async def run_stress_test(self, duration_sec=60):
        """Run stress test for specified duration"""
        print(f"\n🚀 CoAP Stress Test")
        print(f"   Clients: {self.num_clients}")
        print(f"   Request rate: {self.req_rate} req/sec per client")
        print(f"   Total rate: {self.num_clients * self.req_rate} req/sec")
        print(f"   Duration: {duration_sec} seconds")
        print(f"   Server: {self.server_host}:{self.server_port}\n")
        
        # Create client tasks
        tasks = [
            self.client_worker(client_id, duration_sec)
            for client_id in range(self.num_clients)
        ]
        
        # Monitor progress
        start_time = time.time()
        monitor_task = asyncio.create_task(self.monitor_progress(start_time, duration_sec))
        
        # Run all tasks
        await asyncio.gather(*tasks, monitor_task)
        
        elapsed_total = time.time() - start_time
        return {
            'duration': elapsed_total,
            'total_sent': self.metrics['sent'],
            'total_success': self.metrics['success'],
            'total_failures': self.metrics['failures'],
            'avg_latency': sum(self.metrics['latencies']) / len(self.metrics['latencies']) if self.metrics['latencies'] else 0,
            'max_latency': max(self.metrics['latencies']) if self.metrics['latencies'] else 0,
            'min_latency': min(self.metrics['latencies']) if self.metrics['latencies'] else 0,
            'avg_rate': self.metrics['sent'] / elapsed_total if elapsed_total > 0 else 0
        }
    
    async def monitor_progress(self, start_time, duration_sec):
        """Monitor and report progress"""
        last_sent = 0
        while time.time() - start_time < duration_sec + 1:
            current_sent = self.metrics['sent']
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = (current_sent - last_sent) / 1.0
                print(f"[{elapsed:.1f}s] Sent: {current_sent} | Rate: {rate:.0f} req/s | Failures: {self.metrics['failures']}")
            last_sent = current_sent
            await asyncio.sleep(1.0)

def main():
    parser = argparse.ArgumentParser(description='CoAP Stress Test Generator')
    parser.add_argument('--server', default='localhost', help='CoAP server host')
    parser.add_argument('--port', type=int, default=5683, help='CoAP server port')
    parser.add_argument('--clients', type=int, default=10, help='Number of CoAP clients')
    parser.add_argument('--rate', type=int, default=10, help='Request rate per client (req/sec)')
    parser.add_argument('--duration', type=int, default=60, help='Test duration (seconds)')
    
    args = parser.parse_args()
    
    stress_client = CoAPStressClient(
        server_host=args.server,
        server_port=args.port,
        num_clients=args.clients,
        req_rate=args.rate
    )
    
    try:
        results = asyncio.run(stress_client.run_stress_test(duration_sec=args.duration))
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        results = {
            'duration': time.time() - time.time(),
            'total_sent': stress_client.metrics['sent'],
            'total_success': stress_client.metrics['success'],
            'total_failures': stress_client.metrics['failures']
        }
    
    print(f"\n📊 CoAP Stress Test Results")
    print(f"   Duration: {results['duration']:.2f}s")
    print(f"   Total sent: {results['total_sent']}")
    print(f"   Total success: {results['total_success']}")
    print(f"   Total failures: {results['total_failures']}")
    print(f"   Avg latency: {results.get('avg_latency', 0):.2f} ms")
    print(f"   Min/Max latency: {results.get('min_latency', 0):.2f} / {results.get('max_latency', 0):.2f} ms")
    print(f"   Avg rate: {results['avg_rate']:.1f} req/s")
    print(f"   Expected rate: {args.clients * args.rate} req/s")
    
    # Write report
    report = {
        'test': 'week10_coap_stress',
        'timestamp': time.time(),
        'config': {
            'server': args.server,
            'port': args.port,
            'num_clients': args.clients,
            'req_rate_per_client': args.rate,
            'duration': args.duration
        },
        'results': results
    }
    
    report_path = '/tmp/sentrix-week8/week10_coap_stress_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Report saved: {report_path}")

if __name__ == '__main__':
    main()
