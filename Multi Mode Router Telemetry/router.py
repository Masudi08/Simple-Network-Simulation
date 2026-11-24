import socket
import random
import time
import argparse
import threading
import csv
import os
from protocol import unpack_packet,PKT_ACK,PKT_DATA,PKT_FIN

ROUTER_HOST='127.0.0.1'
ROUTER_PORT=5000
RECEIVER_ADDR=('127.0.0.1',6000)
METRICS_FILE='network_metrics.csv'

PKT_NAMES={PKT_DATA:"DATA",PKT_ACK:"ACK",PKT_FIN:"FIN"}

def corrupt_bytes(data:bytes)->bytes:
    '''Flips all bits in one random byte of the packet.'''
    if not data:
        return data
    buf=bytearray(data)
    idx=random.randint(0, len(buf)-1) 
    buf[idx] ^= 0xFF
    return bytes(buf)

class TelemetryLogger:
    '''Thread-safe CSV writer for real-time network metrics.'''
    def __init__(self,filepath:str):
        self.filepath=filepath
        self.lock=threading.Lock()
        self.start_time=time.time()
        self.stats={
            "forwarded":0,
            "dropped":0,
            "corrupted":0,
            "reordered":0,
            "bytes_forwarded":0
        }
        with open(self.filepath,mode='w',newline='') as f:
            writer=csv.writer(f)
            writer.writerow([
                "elapsed_sec","event","direction","pkt_type",
                "seq_num","delay_ms","forwarded","dropped",
                "corrupted","reordered","throughput_kbps"
            ])

    def log_event(self,event:str,direction:str,pkt_type_str:str,seq_num:int,delay_ms:float,pkt_len:int=0):
        with self.lock:
            if event in self.stats:
                self.stats[event] +=1
            if event == "forwarded":
                self.stats["bytes_forwarded"]+=pkt_len

            elapsed=max(time.time()-self.start_time,0.001)
            kbps=(self.stats["bytes_forwarded"]*8)/(elapsed*1000.0)

            with open(self.filepath,mode='a',newline='') as f:
                writer=csv.writer(f)
                writer.writerow([
                    f"{elapsed:.3f}",event,direction,pkt_type_str,
                    seq_num,f"{delay_ms:.1f}",
                    self.stats["forwarded"],self.stats["dropped"],
                    self.stats["corrupted"],self.stats["reordered"],
                    f"{kbps:.2f}"
                ])

def main():
    parser=argparse.ArgumentParser(description="Multimode Network Impairment and Telemetry Router")
    parser.add_argument("--loss",type=float,default=0.15,help="Packet drop probability(0.0 - 1.0)")
    parser.add_argument("--corrupt",type=float,default=0.10,help="Bit corruption probability(0.0 - 1.0)")
    parser.add_argument("--reorder",type=float,default=0.15,help="Out-of-Order spike probability(0.0 - 1.0)")
    parser.add_argument("--min-delay",type=float,default=0.02,help="Minimum propagation delay in seconds")
    parser.add_argument("--max-delay",type=float,default=0.10,help="Maximum normal jitter delay in seconds.")
    args=parser.parse_args()

    logger=TelemetryLogger(METRICS_FILE)
    send_lock=threading.Lock()
    sender_addr=None


    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM,) as router_sock:
        router_sock.bind((ROUTER_HOST,ROUTER_PORT))
        print(f"[ROUTER] Multi-threaded Impairment Engine on {ROUTER_HOST}:{ROUTER_PORT}->{RECEIVER_ADDR}")
        print(f"[ROUTER] Loss={args.loss*100:.0f}% | Corrupt={args.corrupt*200:.0f}% | Reorder={args.reorder*100:.0f}% | Jitter={args.min_delay*1000:.0f}-{args.max_delay*1000:.0f}ms")
        print(f"[ROUTER] Logging live telemetry to ./{METRICS_FILE}\n")

        def transmit_delayed(payload:bytes,dest:tuple,direction:str,pkt_type_str:str,seq:int,delay_ms:float):
            with send_lock:
                try:
                    router_sock.sendto(payload,dest)
                    logger.log_event("forwarded",direction,pkt_type_str,seq,delay_ms,len(payload))
                except OSError:
                    pass#Socket closed during shutdown

        try:
            while True:
                data,src_addr=router_sock.recvfrom(4096)

                #inspect header for telemetry logging
                seq_num,pkt_type,_,_=unpack_packet(data)
                pkt_type_str=PKT_NAMES.get(pkt_type,"UNK")
                seq_display=seq_num if seq_num is not None else -1

                if src_addr== RECEIVER_ADDR:
                    direction="ACK_BACK"
                    dest_addr=sender_addr
                else:
                    sender_addr=src_addr
                    direction="DATA_FWD"
                    dest_addr=RECEIVER_ADDR

                if not dest_addr:
                    continue

                #1.Drop Check
                if random.random() < args.loss:
                    logger.log_event("dropped",direction,pkt_type_str,seq_display,0.0)
                    print(f"[ROUTER] X DROPPED {direction:<8} | {pkt_type_str:<4} SEQ={seq_display:02d}")
                    continue

                #2.Corruption check
                if random.random()<args.corrupt:
                    data=corrupt_bytes(data)
                    logger.log_event("corrupted",direction,pkt_type_str,seq_display,0.0)
                    print(f"[ROUTER] CORRUPTED {direction:<8} | {pkt_type_str:<4} SEQ={seq_display:02d}")

                #3. Jitter & Out-of-Order scheduling
                delay =random.uniform(args.min_delay,args.max_delay)
                if random.random()<args.reorder:
                    #Add a heavy delay spike so subsequent packets overtake this one.
                    delay+=random.uniform(0.25,0.45)
                    logger.log_event("reordered",direction,pkt_type_str,seq_display,delay*1000)
                    print(f"[ROUTER] REORDERED {direction:<8} | {pkt_type_str:<4} SEQ={seq_display:02d} (delayed {delay*1000:.0f}ms)")
                else:
                    print(f"[ROUTER] SCHEDULED {direction:<8} | {pkt_type_str:<4} SEQ={seq_display:02d} ({delay*1000:.0f}ms)")

                #Dispatch non-blocking timer thread so later packets can overtake delayed ones.
                timer=threading.Timer(
                    delay,
                    transmit_delayed,
                    args=(data,dest_addr,direction,pkt_type_str,seq_display,delay*1000)
                )
                timer.daemon=True
                timer.start()
        except KeyboardInterrupt:             
            print(f"\n[ROUTER] Stopped. Final Telemetry Stats: {logger.stats}")

if __name__=="__main__":
    main()
                

        