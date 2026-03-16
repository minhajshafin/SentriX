#!/usr/bin/env python3

"""
Week 10: MQTT Stress Test - Simplified Version
High-volume MQTT traffic for performance testing
"""

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import time
import json
import sys
import threading
from datetime import datetime

class SimpleMQTTStress:
    def __init__(self, broker='localhost', port=1883, num_clients=5, msg_per_client=100):
        self.broker = broker
        self.port = port
        self.num_clients = num_clients
        self.msg_per_client = msg_per_client
        self.metrics = {'published': 0, 'errors': 0}
        self.lock = threading.Lock()
        
    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print(f"Connection failed: {rc}")
    
    def on_publish(self, client, userdata, mid):
        with self.lock:
            self.metrics['published'] += 1
    
    def on_disconnect(self, client, userdata, rc):
        pass
    
    def client_thread(self, client_id):
        """Run MQTT client in thread"""
        try:
            client = mqtt.Client(CallbackAPIVersion.VERSION1, f"stress_client_{client_id}")
            client.on_connect = self.on_connect
            client.on_publish = self.on_publish
            client.on_disconnect = self.on_disconnect
            
            client.connect(self.broker, self.port, keepalive=30)
            client.loop_start()
            
            # Wait for connection
            time.sleep(0.5)
            
            # Publish messages
            for i in range(self.msg_per_client):
                topic = f"stress/client{client_id}/msg{i}"
                payload = json.dumps({'seq': i, 'timestamp': time.time()})
                client.publish(topic, payload, qos=0)
                time.sleep(0.01)  # 100 msg/sec per client
            
            time.sleep(0.5)
            client.loop_stop()
            client.disconnect()
        except Exception as e:
            print(f"Client {client_id} error: {e}")
            with self.lock:
                self.metrics['errors'] += 1
    
    def run(self):
        """Run stress test"""
        print(f"\n🚀 MQTT Stress Test (Simplified)")
        print(f"   Clients: {self.num_clients}")
        print(f"   Messages per client: {self.msg_per_client}")
        print(f"   Total messages: {self.num_clients * self.msg_per_client}")
        print(f"   Broker: {self.broker}:{self.port}\n")
        
        start_time = time.time()
        threads = []
        
        # Start all client threads
        for client_id in range(self.num_clients):
            t = threading.Thread(target=self.client_thread, args=(client_id,))
            t.start()
            threads.append(t)
            time.sleep(0.1)
        
        # Monitor progress
        while any(t.is_alive() for t in threads):
            with self.lock:
                elapsed = time.time() - start_time
                rate = self.metrics['published'] / elapsed if elapsed > 0 else 0
                print(f"[{elapsed:.1f}s] Published: {self.metrics['published']} | Rate: {rate:.0f} msg/s")
            time.sleep(1.0)
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        elapsed_total = time.time() - start_time
        
        print(f"\n📊 Results:")
        print(f"   Duration: {elapsed_total:.2f}s")
        print(f"   Total published: {self.metrics['published']}")
        print(f"   Errors: {self.metrics['errors']}")
        print(f"   Avg rate: {self.metrics['published'] / elapsed_total:.1f} msg/s")
        
        return {
            'test': 'week10_mqtt_stress',
            'timestamp': datetime.now().isoformat(),
            'config': {
                'num_clients': self.num_clients,
                'msg_per_client': self.msg_per_client
            },
            'results': {
                'duration': elapsed_total,
                'published': self.metrics['published'],
                'errors': self.metrics['errors'],
                'rate': self.metrics['published'] / elapsed_total
            }
        }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MQTT Stress Test')
    parser.add_argument('--broker', default='localhost')
    parser.add_argument('--port', type=int, default=1883)
    parser.add_argument('--clients', type=int, default=5)
    parser.add_argument('--msgs', type=int, default=100)
    
    args = parser.parse_args()
    
    stress = SimpleMQTTStress(
        broker=args.broker,
        port=args.port,
        num_clients=args.clients,
        msg_per_client=args.msgs
    )
    
    results = stress.run()
    
    # Save report
    with open('/tmp/sentrix-week8/week10_mqtt_stress_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Report saved to /tmp/sentrix-week8/week10_mqtt_stress_results.json\n")
