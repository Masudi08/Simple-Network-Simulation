#This update of receiver.py adds crc validation and binary acks.
import socket
from protocol import unpack_packet, pack_packet,PKT_DATA,PKT_ACK,PKT_FIN

HOST='127.0.0.1'
PORT=6000

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as recv_sock:
        recv_sock.bind((HOST,PORT))
        print(f"[RECEIVER] Binary UDP receiver bound to {HOST}:{PORT}...")

        expected_seq=0

        while True:
            raw_data,router_addr=recv_sock.recvfrom(4096)
            seq_num,pkt_type,payload,is_valid=unpack_packet(raw_data)

            #reject corrupted datagrams caught by crc32
            if not is_valid:
                print(f"[RECEIVER] ! CRC32 MISMATCH on incoming packet ({len(raw_data)}B). Discarding.")
                continue

            if pkt_type == PKT_FIN:
                print(f"[RECEIVER] FIN received (SEQ={seq_num}). Resetting session state.")
                ack=pack_packet(seq_num,PKT_ACK)
                recv_sock.sendto(ack,router_addr)
                expected_seq=0
                continue

            if pkt_type==PKT_DATA:
                if seq_num==expected_seq:
                    message=payload.decode('utf-8',errors='replace')
                    print(f"[RECEIVER] Accepted SEQ={seq_num} ({len(payload)}B): '{message}'")
                    expected_seq+=1
                elif seq_num < expected_seq:
                    print(f"[RECEIVER] Dupllicate SEQ={seq_num}. Re-sending ACK.")
                else:
                    print(f"[RECEIVER] OUT OF ORDER SEQ={seq_num} (expected {expected_seq}). Ignoring")
                    continue

                #Send 11-byte binary ACK back through router.
                ack_pkt=pack_packet(seq_num,PKT_ACK)
                recv_sock.sendto(ack_pkt,router_addr)

if __name__=="__main__":
    main()
