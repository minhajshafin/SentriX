import socket

HOST = "0.0.0.0"
PORT = 5683

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print(f"[coap-backend-stub] listening on {HOST}:{PORT}/udp")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"[coap-backend-stub] recv {len(data)} bytes from {addr}")
    sock.sendto(data, addr)
