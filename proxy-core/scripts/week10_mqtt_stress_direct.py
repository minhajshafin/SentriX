#!/usr/bin/env python3

"""
Week 10: Direct MQTT Stress Test
Uses socket-level MQTT protocol to avoid client library issues
"""

import socket
import json
import time
import sys
import threading
from datetime import datetime

def send_mqtt_packet(host, port, client_id, messages=100):
    """Send MQTT packets directly via socket"""
    sock = socket.create_connection((host, port), timeout=5)
    time.sleep(0.1)
    
    # MQTT CONNECT packet
    connect_packet = bytes([
        0x10, 0x3f,  # Fixed header: CONNECT
        0x00, 0x04,  # Remaining length
        0x4d, 0x51, 0x54, 0x54,  # Protocol name: MQTT
        0x04,  # Protocol level
        0x02,  # Connect flags: clean session
        0x00, 0x3c,  # Keep alive: 60 seconds
        0x00, len(client_id),  # Client ID length
        *client_id.encode()  # Client ID
    ])
    
    sock.send(connect_packet)
    
    # Receive CONNACK
    connack = sock.recv(4)
    if connack[0] != 0x20:  # CONNACK fixed header
        print(f"Client {client_id}: CONNACK failed")
        sock.close()
        return 0
    
    # Send PUBLISH packets
    pub_count = 0
    for i in range(messages):
        topic = f"stress/test/{client_id}/msg{i}"
        payload = json.dumps({'seq': i, 'ts': time.time()}).encode()
        
        # Minimal MQTT PUBLISH packet
        publish_packet = bytearray([0x30])  # PUBLISH fixed header
        
        # Topic string length (2 bytes) + Topic + Payload
        remaining_len = 2 + len(topic) + len(payload)
        
        # Encode remaining length
        if remaining_len < 128:
            publish_packet.append(remaining_len)
        else:
            publish_packet.append((remaining_len % 128) | 0x80)
            publish_packet.append(remaining_len // 128)
        
        # Topic
        publish_packet.extend(len(topic).to_bytes(2, 'big'))
        publish_packet.extend(topic.encode())
        
        # Payload
        publish_packet.extend(payload)
        
        try:
            sock.send(bytes(publish_packet))
            pub_count += 1
        except Exception as e:
            print(f"Client {client_id}: Publish error on message {i}: {e}")
            break
    
    # DISCONNECT
    sock.send(bytes([0xe0, 0x00]))
    sock.close()
    
    return pub_count

def run_mqtt_stress(broker='localhost', port=1883, num_clients=5, msgs_per_client=100):
    """Run MQTT stress test"""
    print(f"\n🚀 MQTT Stress Test (Socket-based)")
    print(f"   Broker: {broker}:{port}")
    print(f"   Clients: {num_clients}")
    print(f"   Messages per client: {msgs_per_client}")
    print(f"   Total messages: {num_clients * msgs_per_client}\n")
    
    start_time = time.time()
    results = {'total': 0, 'errors': 0}
    lock = threading.Lock()
    
    def client_task(client_id):
        try:
            count = send_mqtt_packet(broker, port, f"stress_client_{client_id}", msgs_per_client)
            with lock:
                results['total'] += count
                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Client {client_id}: {count}/{msgs_per_client} published")
        except Exception as e:
            print(f"Client {client_id} failed: {e}")
            with lock:
                results['errors'] += 1
    
    threads = []
    for client_id in range(num_clients):
        t = threading.Thread(target=client_task, args=(client_id,))
        t.start()
        threads.append(t)
        time.sleep(0.05)
    
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 Results:")
    print(f"   Duration: {elapsed:.2f}s")
    print(f"   Total published: {results['total']}")
    print(f"   Errors: {results['errors']}")
    print(f"   Rate: {results['total']/elapsed:.1f} msg/s")
    
    return {
        'test': 'week10_mqtt_stress_socket',
        'timestamp': datetime.now().isoformat(),
        'broker': f"{broker}:{port}",
        'config': {'num_clients': num_clients, 'msgs_per_client': msgs_per_client},
        'results': {
            'duration': elapsed,
            'published': results['total'],
            'errors': results['errors'],
            'rate': results['total'] / elapsed
        }
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', default='localhost')
    parser.add_argument('--port', type=int, default=1883)
    parser.add_argument('--clients', type=int, default=5)
    parser.add_argument('--msgs', type=int, default=100)
    
    args = parser.parse_args()
    report = run_mqtt_stress(args.broker, args.port, args.clients, args.msgs)
    
    with open('/tmp/sentrix-week8/week10_mqtt_stress.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Report saved: /tmp/sentrix-week8/week10_mqtt_stress.json\n")
