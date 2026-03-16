#!/usr/bin/env python3

"""
Week 10: MQTT Stress Test Generator
Sustained high-volume MQTT traffic for performance and detection validation
"""

import paho.mqtt.client as mqtt
import time
import json
import sys
import threading
import argparse
from collections import defaultdict

class MQTTStressClient:
    def __init__(self, broker_host='localhost', broker_port=1883, num_clients=10, msg_rate=10):
        """
        Args:
            broker_host: MQTT broker address
            broker_port: MQTT broker port
            num_clients: Number of concurrent MQTT clients to spawn
            msg_rate: Messages per second per client
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.num_clients = num_clients
        self.msg_rate = msg_rate
        self.clients = []
        self.metrics = {
            'published': 0,
            'received': 0,
            'errors': 0,
            'latencies': []
        }
        self.lock = threading.Lock()
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe('stress/test/#')
        else:
            with self.lock:
                self.metrics['errors'] += 1
    
    def on_message(self, client, userdata, msg):
        with self.lock:
            self.metrics['received'] += 1
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            with self.lock:
                self.metrics['errors'] += 1
    
    def publish_worker(self, client_id, duration_sec):
        """Publish messages at configured rate"""
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"stress_publisher_{client_id}")
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        
        try:
            client.connect(self.broker_host, self.broker_port, keepalive=30)
            client.loop_start()
            
            start_time = time.time()
            msg_count = 0
            interval = 1.0 / self.msg_rate  # Time between messages
            
            topics = [
                f'stress/test/mqtt/client_{client_id}/telemetry',
                f'stress/test/mqtt/client_{client_id}/status',
                f'stress/test/mqtt/client_{client_id}/control'
            ]
            
            while time.time() - start_time < duration_sec:
                topic = topics[msg_count % len(topics)]
                payload = json.dumps({
                    'client_id': client_id,
                    'seq': msg_count,
                    'timestamp': time.time(),
                    'value': msg_count % 100
                })
                
                try:
                    client.publish(topic, payload, qos=1)
                    with self.lock:
                        self.metrics['published'] += 1
                    msg_count += 1
                except Exception as e:
                    with self.lock:
                        self.metrics['errors'] += 1
                    print(f"Publish error (client {client_id}): {e}")
                
                time.sleep(interval)
            
            client.loop_stop()
            client.disconnect()
        except Exception as e:
            print(f"Client {client_id} error: {e}")
            with self.lock:
                self.metrics['errors'] += 1
    
    def run_stress_test(self, duration_sec=60):
        """Run stress test for specified duration"""
        print(f"\n🚀 MQTT Stress Test")
        print(f"   Clients: {self.num_clients}")
        print(f"   Message rate: {self.msg_rate} msg/sec per client")
        print(f"   Total rate: {self.num_clients * self.msg_rate} msg/sec")
        print(f"   Duration: {duration_sec} seconds")
        print(f"   Broker: {self.broker_host}:{self.broker_port}\n")
        
        threads = []
        start_time = time.time()
        
        # Start publisher threads
        for client_id in range(self.num_clients):
            t = threading.Thread(target=self.publish_worker, args=(client_id, duration_sec))
            t.start()
            threads.append(t)
            time.sleep(0.1)  # Stagger client startup
        
        # Monitor progress
        last_count = 0
        while time.time() - start_time < duration_sec + 2:
            with self.lock:
                current_count = self.metrics['published']
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = (current_count - last_count) / 1.0
                    print(f"[{elapsed:.1f}s] Published: {current_count} | Rate: {rate:.0f} msg/s | Errors: {self.metrics['errors']}")
                last_count = current_count
            time.sleep(1.0)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        elapsed_total = time.time() - start_time
        return {
            'duration': elapsed_total,
            'total_published': self.metrics['published'],
            'total_received': self.metrics['received'],
            'total_errors': self.metrics['errors'],
            'avg_rate': self.metrics['published'] / elapsed_total if elapsed_total > 0 else 0
        }

def main():
    parser = argparse.ArgumentParser(description='MQTT Stress Test Generator')
    parser.add_argument('--broker', default='localhost', help='MQTT broker host')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--clients', type=int, default=10, help='Number of MQTT clients')
    parser.add_argument('--rate', type=int, default=10, help='Message rate per client (msg/sec)')
    parser.add_argument('--duration', type=int, default=60, help='Test duration (seconds)')
    
    args = parser.parse_args()
    
    stress_client = MQTTStressClient(
        broker_host=args.broker,
        broker_port=args.port,
        num_clients=args.clients,
        msg_rate=args.rate
    )
    
    results = stress_client.run_stress_test(duration_sec=args.duration)
    
    print(f"\n📊 MQTT Stress Test Results")
    print(f"   Duration: {results['duration']:.2f}s")
    print(f"   Total published: {results['total_published']}")
    print(f"   Total received: {results['total_received']}")
    print(f"   Total errors: {results['total_errors']}")
    print(f"   Avg rate: {results['avg_rate']:.1f} msg/s")
    print(f"   Expected rate: {args.clients * args.rate} msg/s")
    
    # Write report
    report = {
        'test': 'week10_mqtt_stress',
        'timestamp': time.time(),
        'config': {
            'broker': args.broker,
            'port': args.port,
            'num_clients': args.clients,
            'msg_rate_per_client': args.rate,
            'duration': args.duration
        },
        'results': results
    }
    
    report_path = '/tmp/sentrix-week8/week10_mqtt_stress_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Report saved: {report_path}")

if __name__ == '__main__':
    main()
