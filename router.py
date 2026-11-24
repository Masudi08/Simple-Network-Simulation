import socket 
import random
import time

ROUTER_HOST = '127.0.0.1'
ROUTER_PORT = 5000 #As seen in the receiver_udp.py file.
RECEIVER_ADDR = ('127.0.0.1',6000)

DROP_RATE= 0.25 #25% Packet loss
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as router_sock:
    router_sock.bind((ROUTER_HOST,ROUTER_PORT))
    print(f"[ROUTER] Active on {ROUTER_HOST}:{ROUTER_PORT}-> Forwarding to {RECEIVER_ADDR}")
    print(f"[ROUTER] Simulating {int(DROP_RATE * 100)}% packet loss...\n")

    sender_addr=None

    while True:
        data, src_addr=router_sock.recvfrom(4096)

        #simulation of network propagation delay.(50-200ms)
        time.sleep(random.uniform(0.05,0.2))

        #Randomization(rolling the dice) to simulate packet loss in transit
        if random.random()<DROP_RATE:
            print(f"[ROUTER] X DROPPED packet from {src_addr}:{data.decode('utf-8')}")
            continue

        #Routing logic: traffic from receiver goes back to sender, traffic from sender goes to receiver.
        if src_addr==RECEIVER_ADDR:
            if sender_addr:
                print(f"[ROUTER] <- Forwading ACK to Sender {sender_addr}")
                router_sock.sendto(data, sender_addr)
        else:
            sender_addr=src_addr# Record the sender's ephemeral port.
            print(f"[ROUTER] -> Forwarding DATA to Receiver {RECEIVER_ADDR}")
            router_sock.sendto(data,RECEIVER_ADDR)