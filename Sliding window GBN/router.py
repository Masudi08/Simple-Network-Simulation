#Adds bit construction and CLI flags
import socket
import random
import time
import argparse

ROUTER_HOST='127.0.0.1'
ROUTER_PORT=5000
RECEIVER_ADDR=('127.0.0.1',6000)

def corrupt_bytes(data:bytes)->bytes:
    """Flips a random bit in a mutable bytearray copy of the packet"""
    if not data:
        return data
    buf=bytearray(data)
    idx=random.randint(0,len(buf)-1)
    buf[idx]^=0xFF#invert all bits in that single byte
    return bytes(buf)
def main():
    parser=argparse.ArgumentParser(description="Unreliable UDP Network Router Simulator")
    parser.add_argument("--loss",type=float,default=0.20,help="Packet Drop probability(0.0-1.0)")
    parser.add_argument("--corrupt",type=float,default=0.15,help="Packet Corruption Probability(0.0-0.1)")
    args=parser.parse_args()

    stats={"forwarded":0,"dropped":0,"corrupted":0}

    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as router_sock:
        router_sock.bind((ROUTER_HOST,ROUTER_PORT))
        print(f"[ROUTER] Listening on {ROUTER_HOST}:{ROUTER_PORT}->{RECEIVER_ADDR}")
        print(f"[ROUTER] Loss Rate:{args.loss*100:.0f}% | Corruption Rate: {args.corrupt*100:.0f}%\n")

        sender_addr=None

        try:
            while True:
                data,src_addr=router_sock.recvfrom(4096)
                time.sleep(random.uniform(0.03,0.12)) #simulated propagation jitter.

                #PACKET DROP SIMULATION
                if random.random()<args.loss:
                    stats["dropped"]+=1
                    print(f"[ROUTER] X DROPPED ({len(data)}B) from {src_addr} | Stats:{stats}")
                    continue
                #SIMULATION OF BIT-LEVEL CORRUPTION IN TRANSIT
                if random.random()<args.corrupt:
                    data=corrupt_bytes(data)
                    stats["corrupted"]+=1
                    print(f"[ROUTER] CORRUPTED ({len(data)}B) from {src_addr} | Stats: {stats}")

                #ROUTING PACKET TO DESTINATION
                if src_addr==RECEIVER_ADDR:
                    if sender_addr:
                        stats["forwarded"]+=1
                        router_sock.sendto(data,RECEIVER_ADDR)
                else:
                    sender_addr=src_addr
                    stats["forwarded"]+=1
                    router_sock.sendto(data,RECEIVER_ADDR)
        except KeyboardInterrupt:            
            print(f"\n[ROUTER] Shutting down. Final stats: {stats}")
if __name__ == "__main__":
    main()