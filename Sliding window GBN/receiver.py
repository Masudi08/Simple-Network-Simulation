#cumulative ACK receiver. Tracks expected_seq. Whenever an out-of-order packet arrives(or a duplicate), it retransmits the cumulative ACK 
#for expected_seq-1.

import socket
from protocol import unpack_packet,pack_packet,PKT_ACK,PKT_DATA,PKT_FIN

HOST='127.0.0.1'
PORT=6000

def main():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as recv_sock:
        recv_sock.bind((HOST,PORT))
        print(f"[RECEIVER - GBN] Listening on {HOST}:{PORT}...")

        expected_seq=0

        while True:
            raw_data, router_addr=recv_sock.recvfrom(4096)
            seq_num,pkt_type,payload,is_valid=unpack_packet(raw_data)

            if not is_valid:
                print(f"[RECEIVER] CRC32 Failed on incoming packet. Discarding.")
                continue

            if pkt_type==PKT_FIN:
                print(f"[RECEIVER] FIN received (SEQ={seq_num}). Session complete. Resetting.\n")
                recv_sock.sendto(pack_packet(seq_num,PKT_ACK),router_addr)
                expected_seq=0
                continue

            if pkt_type==PKT_DATA:
                if seq_num==expected_seq:
                    msg=payload.decode('utf-8',errors='replace')
                    print(f"[RECEIVER] Accepted in-order SEQ={seq_num:02d}:'{msg}'")
                    #Send cumulative ACK for this sequence number.
                    recv_sock.sendto(pack_packet(expected_seq,PKT_ACK),router_addr)
                    expected_seq+=1
                else:
                    #Out of order or duplicate packet: discard payload and re-ACK last valid SEQ
                    last_valid=expected_seq-1
                    print(f"[RECEIVER]Out-of-Order SEQ={seq_num:02d} (expected {expected_seq:02d}). Re-ACKing {last_valid}")
                    if last_valid >=0:
                        recv_sock.sendto(pack_packet(last_valid,PKT_ACK),router_addr)


if __name__ == "__main__":
    main()