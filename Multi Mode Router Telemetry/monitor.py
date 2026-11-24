import csv
import os
import time
from collections import deque

METRICS_FILE='network_metrics.csv'
REFRESH_INTERVAL=0.25 #4 FPS live dashboard refresh

#ANSI Terminal Color Codes
RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[96m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
MAGENTA="\033[95m"
DIM="\033[2m"

def make_bar(count:int,total:int,width:int=28,color:str=GREEN)->str:
    '''Renders a proportional ASCII progress bar.'''
    if total<=0:
        filled=0
    else:
        filled=int((count/total)*width)
    filled=max(0,min(width,filled))
    bar="⬜"*filled+"⬛"*(width-filled)
    pct=(count/total*100) if total > 0 else 0.0
    return f"{color}{bar}{RESET} {count:>4} ({pct:5.1f}%)"

def clear_screen():
    '''Moves cursor to top-left and clears screen without flicker.'''
    print("\033[H\033[J", end="")

def read_telemetry(filepath:str):
    '''Reads all rows from network_metrics.csv and computes live aggregates.'''
    if not os.path.exists(filepath):
        return None
    rows=[]
    with open(filepath,mode='r',newline='') as f:
        reader=csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        return None

    latest=rows[-1]
    recent_events=deque(rows[-8:],maxlen=8)

    #calculate average propagation delay across forwarded/reordered packets
    delays=[float(r["delay_ms"]) for r in rows if float(r["delay_ms"]) > 0]
    avg_delay=sum(delays)/len(delays) if delays else 0.0
    max_delay=max(delays) if delays else 0.0

    #Track per direction counts
    data_fwd=sum(1 for r in rows if r["direction"]=="DATA_FWD" and r["event"]=="forwarded")
    ack_back=sum(1 for r in rows if r["direction"]=="ACK_BACK" and r["event"]=="forwarded")

    return{
        "elapsed":float(latest["elapsed_sec"]),
        "forwarded":int(latest["forwarded"]),
        "dropped":int(latest["dropped"]),
        "corrupted":int(latest["corrupted"]),
        "reordered":int(latest["reordered"]),
        "throughput_kbps":float(latest["throughput_kbps"]),
        "avg_delay":avg_delay,
        "max_delay":max_delay,
        "data_fwd": data_fwd,
        "ack_back": ack_back,
        "recent": recent_events
    }

def render_dashboard(data:dict):
    clear_screen()
    total_events=data["forwarded"]+data["dropped"]

    print(f"{BOLD}{CYAN}==============================================================={RESET}")
    print(f"{BOLD}{CYAN}||       UDP SLIDING-WINDOW NETWORK TELEMETRY MONITOR(LIVE)  ||{RESET}")
    print(f"{BOLD}{CYAN}==============================================================={RESET}")
    print(f"{BOLD}Uptime:{RESET} {data['elapsed']:6.2f}s  |  "
        f"{BOLD}Throughput:{RESET} {GREEN}{data['throughput_kbps']:6.2f} kbps{RESET}  |  "
        f"{BOLD}Avg Jitter:{RESET} {YELLOW}{data['avg_delay']:5.1f} ms{RESET} (Peak: {data['max_delay']:.0f} ms)")
    print(f"{DIM}{'-'*72}{RESET}")

    print(f"\n {BOLD}TRAFFIC HEALTH BREAKDOWN (Total Handled: {total_events}){RESET}")
    print(f" Forwarded : {make_bar(data['forwarded'],total_events,color=GREEN)}")
    print(f" Dropped : {make_bar(data['dropped'],total_events,color=RED)}")
    print(f" corrupted : {make_bar(data['corrupted'],max(data['forwarded'],1),color=GREEN)}")
    print(f" Reordered : {make_bar(data['reordered'],max(data['forwarded'],1),color=MAGENTA)}")

    print(f"\n {BOLD}DIRECTIONAL FLOW{RESET}")
    print(f" Sender -> Receiver (DATA) : {CYAN}{data['data_fwd']} frames{RESET}  |  "
          f"Receiver -> Sender (ACK) : {CYAN}{data['ack_back']} frames{RESET}")

    print(f"\n {BOLD}LIVE PACKET EVENT STREAM (Last 8 Events){RESET}")
    print(f" {BOLD}{'TIME(s)':<8} {'EVENT':<11} {'DIR':<10} {'TYPE':<6} {'SEQ':<5} {'DELAY':<9}{RESET}")

    for ev in data["recent"]:
        ev_name=ev["event"].upper()
        if ev_name=="DROPPED":
            color=RED
        elif ev_name=="CORRUPTED":
            color=YELLOW
        elif ev_name=="REORDERED":
            color=MAGENTA
        else:
            color=GREEN

        delay_str=f"{float(ev['delay_ms']):.0f}ms" if float(ev["delay_ms"])>0 else "-"
        print(f" {float(ev['elapsed_sec']):<8.2f} {color}{ev_name:<11}{RESET}"
            f"{ev['direction']:<10} {ev['pkt_type']:<6} {int(ev['seq_num']):<5} {delay_str:<9}")

    print(f"\n{DIM} Press Ctrl+C to exit monitor.{RESET}")

def main():
    clear_screen()
    print(f"{CYAN}[MONITOR] Waiting for {METRICS_FILE} from router.py...{RESET}")
    try:
        while True:
            telemetry=read_telemetry(METRICS_FILE)
            if telemetry:
                render_dashboard(telemetry)
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n{CYAN}[MONITOR] Dashboard closed.{RESET}")

if __name__=="__main__":
    main()
   