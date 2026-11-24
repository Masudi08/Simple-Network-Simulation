import socket
import json
import time

ROUTER_ADDR=('127.0.0.1',5000)
TIMEOUT_SEC = 1.0

messages= [
    "Handshake sindio",
    "Sensor Telemetry:24.5C",
    "Route Table Update",
    "Config Payload"
    "Session Close"
]

with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as send_sock:
    #Crucial for reliability: if no ACK arrives within 1.0s, raise socket.timeout
    send_sock.settimeout(TIMEOUT_SEC)

    for seq_num, text in enumerate(messages):
        #Encapsulate payload with a sequence number header
        packet=json.dumps({'seq':seq_num,'data':text}).encode('utf-8')
        acknowledged=False

        while not acknowledged:
            try:
                print(f"[SENDER] Sending SEQ={seq_num}:'{text}'")
                send_sock.sendto(packet, ROUTER_ADDR)

                #Wait for ACK from router
                ack_raw,_=send_sock.recvfrom(4096)
                ack_data = json.loads(ack_raw.decode('utf-8'))

                if ack_data.get('ack')==seq_num:
                    print(f"[SENDER] Received ACK for SEQ={seq_num}\n")
                    acknowledged=True
            except socket.timeout:
                #Packet or ACK was lost in the router hence loop repeats and retransmits.
                print(f"[SENDER] !Timeout waiting for ACK={seq_num}. Retransmitting...")

print("[SENDER] All messages reliably delivered over unreliable UDP.")

