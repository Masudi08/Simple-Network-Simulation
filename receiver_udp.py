import socket
import json

HOST='127.0.0.1'
PORT=6000

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as recv_sock:
#SOCK_DGRAM specifies UDP i.e connectionless datagrams.
    recv_sock.bind((HOST,PORT))
    print(f"[RECEIVER] UDP socket bound to {HOST}:{PORT}, waiting for packets...")

    expected_sequence=0

    while True:
        raw_data, router_addr = recv_sock.recvfrom(4096)
        #recvfrom() blocks until a single UDP datagram arrives.

        #Parsing my custom application-layer header and payload.
        packet=json.loads(raw_data.decode('utf-8'))
        seq_num=packet['seq']
        payload=packet['data']

        if seq_num==expected_sequence:
            print(f"[RECEIVER] Accepted SEQ={seq_num}: '{payload}")
            expected_sequence+=1
        elif seq_num<expected_sequence:
            print(f"[RECEIVER] Duplicate SEQ={seq_num} detected (already processed). Resend ACK")
            #Happens if the previous ACK was dropped by the router and the sender retried.
        else:
            print(f"[RECEIVER] Out-of-Order SEQ={seq_num} (expected {expected_sequence}). Ignoring")
            continue

        #Building and transmitting an ACK packet back to the router.    
        ack_packet=json.dumps({'ack':seq_num}).encode('utf-8')
        recv_sock.sendto(ack_packet,router_addr)