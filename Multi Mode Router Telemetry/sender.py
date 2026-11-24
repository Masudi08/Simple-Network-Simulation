"""Sliding window plus non-blocking /short-poll event loop
    Instead of blocking after every packet, this file uses a short socket timout(0.5s) to run a continuous event loop that:
        1. Sends new packets whenever next_seq < base + WINDOW_SIZE.
        2. Reads any incoming cumulative ACKs and slides base forward.
        3. Checks if time.time() - timer_start > TIMEOUT_SEC; if so, retransmits the entire active window (base to next_seq-1)"""

import socket
import time
from protocol import pack_packet,unpack_packet,PKT_ACK,PKT_DATA,PKT_FIN

ROUTER_ADDR = ('127.0.0.1',5000)
WINDOW_SIZE=4
TIMEOUT_SEC=1.0
TOTAL_PACKETS=40

def format_window(base:int,next_seq: int,total: int)->str:
    '''Visualizes the sliding window state in the terminal.'''
    slots=[]
    for i in range(base,min(base+WINDOW_SIZE,total)):
        status="SENT" if i < next_seq else "READY"
        slots.append(f"{i:02d}:{status}")
    return "[" + " | ".join(slots) + "]"

def main():
    #Prebuilding all binary data packets in a buffer indexed by sequence number.
    packets=[
        pack_packet(seq,PKT_DATA,f"Stream block #{seq:02d} | payload_ok".encode('utf-8'))
        for seq in range(TOTAL_PACKETS)
    ]

    base=0              #Oldest acknowledged packet.
    next_seq=0          #Next sequence number to send.
    timer_start=None    #Timer for the base packet.
    total_sent=0
    retransmission=0
    start_time=time.time()

    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as send_sock:
        #Short poll timeout so the timer can send, receive and check timers concurrently.
        send_sock.settimeout(0.05)

        print(f"[SENDER-GBN] Starting transfer: {TOTAL_PACKETS} packets | Window size={WINDOW_SIZE}\n")

        while base < TOTAL_PACKETS:
            #1.TRANSMIT: Send packets while window has open slots
            while next_seq < base + WINDOW_SIZE and next_seq < TOTAL_PACKETS:
                send_sock.sendto(packets[next_seq],ROUTER_ADDR)
                total_sent+=1
                if base == next_seq:
                    timer_start = time.time() #Start timer for the oldest unACKed packet.
                next_seq+=1
                print(f"[SENDER] -> Sent SEQ={next_seq-1:02d} | Window: {format_window(base, next_seq, TOTAL_PACKETS)}")

            #2.RECEIVE: Poll for incoming cumulative ACKs
            try:
                ack_raw,_ = send_sock.recvfrom(4096)
                ack_seq,ack_type,_,is_valid = unpack_packet(ack_raw)

                if not is_valid:
                    print(f"[SENDER] Corrupted ACK ignored.")
                elif ack_type==PKT_ACK and ack_seq >=base:
                    #Cumulative ACK slides the window forward past ack_seq
                    base=ack_seq+1
                    print(f"[SENDER] Cumulative ACK={ack_seq:02d} | Window slid to base={base:02d}")
                    if base == next_seq:
                        timer_start=None #All in-flight packets are ACKed.
                    else:
                        timer_start=time.time() #Restart timer for new 'base'
            except socket.timeout:
                pass #No ack arrived during this 50ms poll; proceed to timer check.

            #3. TIMEOUT CHECK: If 'base' packet expired, Go-Back-N and resend window.
            if timer_start is not None and (time.time()-timer_start)>TIMEOUT_SEC:
                window_count=next_seq-base
                print(f"\n [SENDER] ! TIMEOUT on base={base:02d}! Going back to resend {window_count} packet(s) ({base:02d}..{next_seq-1:02d})")
                timer_start=time.time()
                for seq in range(base, next_seq):
                    send_sock.sendto(packets[seq],ROUTER_ADDR)
                    total_sent+=1
                print()

        #4. SEND FIN: Cleanly close session
        fin_pkt=pack_packet(TOTAL_PACKETS,PKT_FIN)
        send_sock.settimeout(0.6)
        while True:
            send_sock.sendto(fin_pkt,ROUTER_ADDR)
            try:
                ack_raw,_=send_sock.recvfrom(4096)
                ack_seq,ack_type,_,is_valid=unpack_packet(ack_raw)
                if is_valid and ack_type ==PKT_ACK and ack_seq ==TOTAL_PACKETS:
                    break
            except socket.timeout:
                continue

    elapsed=time.time()-start_time
    print("\n---GO-BACK-N SUMMARY ---")
    print(f"Window size: {WINDOW_SIZE}")
    print(f"Unique packets: {TOTAL_PACKETS}")
    print(f"Total packets Tx: {total_sent} ({retransmission} retransmitted)")
    print(f"Elapsed Time: {elapsed:.2f}s")

if __name__== "__main__":
    main()

