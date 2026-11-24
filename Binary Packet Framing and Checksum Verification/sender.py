#This update of sender.py will add Binary Framing and Session Teardown
import socket 
import time
from protocol import pack_packet,unpack_packet,PKT_DATA,PKT_ACK,PKT_FIN

ROUTER_ADDR=('127.0.0.1',5000)
TIMEOUT_SEC=0.6

def send_reliable(sock:socket.socket,seq_num:int,pkt_type:int,payload:bytes=b"")-> int:
    """Sends a single binary packet and blocks until a valid matching ACK arrives."""
    packet=pack_packet(seq_num,pkt_type,payload)
    attempts=0

    while True:
        attempts+=1
        sock.sendto(packet,ROUTER_ADDR)

        try:
            ack_raw,_=sock.recvfrom(4096)
            ack_seq,ack_type,_,is_valid= unpack_packet(ack_raw)

            if not is_valid:
                print(f"[SENDER] Corrupted ACK received for SEQ={seq_num}. Retrying...")
                continue

            if ack_type==PKT_ACK and ack_seq==seq_num:
                return attempts
        except socket.timeout:
            print(f"[SENDER] TIMEOUT on SEQ={seq_num} (Attempt {attempts}). Retransmitting...")

def main():
    total_packets=15
    total_transmissions=0
    start_time=time.time()

    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as send_sock:
        send_sock.settimeout(TIMEOUT_SEC)

        for seq in range(total_packets):
            msg=f"Telemetry frame #{seq:02d} | CPU=42% | MEM=68%".encode('utf-8')
            attempts=send_reliable(send_sock,seq,PKT_DATA,msg)
            total_transmissions+=attempts
            print(f"[SENDER] SEQ={seq:02d} ACKed (Attempts: {attempts})")

        #Graceful binary FIN handshake.
        fin_attempts=send_reliable(send_sock,total_packets,PKT_FIN)
        total_transmissions+=fin_attempts

    elapsed=time.time()-start_time
    print("\n --- TRANSMISSION SUMMARY---")
    print(f"Unique packets: {total_packets}")
    print(f"Total Attempts:{total_transmissions} ({total_transmissions-total_packets} retransmissions)")
    print(f"Total Time    : {elapsed:.2f}S")

if __name__== "__main__":
    main()

