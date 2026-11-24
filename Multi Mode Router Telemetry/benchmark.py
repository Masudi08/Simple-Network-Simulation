#Instead of manually starting or stopping terminals to test different network conditions, this file will orchestrate receiver.py and router.py
#automatically across the 4 profiles and summarizes the results.

import subprocess
import sys
import time 
import csv
import re

SCENARIOS=[
    {"name":"1.Ideal LAN",         "loss":0.00, "corrupt":0.00, "reorder":0.00},
    {"name":"2. Light Jitter",     "loss":0.05, "corrupt":0.05, "reorder":0.10},
    {"name":"3. Lossy Wi-Fi",      "loss":0.15, "corrupt":0.10, "reorder":0.15},
    {"name":"4. Severe Link Drop", "loss":0.30, "corrupt":0.15, "reorder":0.20}
]

def parse_sender_summary(output:str):
    '''Extracts total transmitted packets and elapsed time from sender.py stdout.'''
    tx_match=re.search(r"Total Packets Tx\s*:\s*(\d+)\s*\((\d+)\s*retransmitted\)",output)
    time_match=re.search(r"Elapsed Time\s*:\s*([\d.]+)s",output)
    unique_match=re.search(r"Unique Packets\s*:\s*(\d+)",output)

    unique=int(unique_match.group(1) if unique_match else 0)
    total_tx=int(tx_match.group(1)) if tx_match else 0
    retx=int(tx_match.group(2)) if tx_match else 0
    elapsed=float(time_match.group(1)) if time_match else 0.0
    return unique,total_tx,retx,elapsed

def read_final_router_metrics(csv_path="network_metrics.csv"):
    '''Reads final through-put and event counts from the router's CSV log.'''
    try:
        with open(csv_path,mode="r",newline="") as f:
            rows=list(csv.DictReader(f))
            if not rows:
                return 0.0, 0 , 0
            last=rows[-1]
            return float(last["throughput_kbps"]), int(last["dropped"]), int(last["corrupted"])
    except FileNotFoundError:
        return 0.0,0,0

def run_benchmark():
    print("Starting automated UDP sliding-window benchmark suite...\n")
    results=[]

    for sc in SCENARIOS:
        print(f"Running Scenario: {sc['name']} (loss={sc['loss']}, corrupt={sc['corrupt']}, reorder={sc['reorder']})...")

        recv_proc=subprocess.Popen(
            [sys.executable,"receiver.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        router_proc=subprocess.Popen(
            [
                sys.executable,"router.py",
                "--loss",str(sc["loss"]),
                "--corrupt",str(sc["corrupt"]),
                "--reorder",str(sc["reorder"])
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        #Allow sockets to bind before starting sender
        time.sleep(0.4)

        try:
            sender_res=subprocess.run(
                [sys.executable,"sender.py"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            unique,total_tx,retx,elapsed=parse_sender_summary(sender_res.stdout)
            kbps,dropped,corrupted=read_final_router_metrics()
            efficiency=(unique/total_tx*100)if total_tx > 0 else 0.0

            results.append({
                "scenario":sc["name"],
                "elapsed":f"{elapsed:.2f}s",
                "total_tx":total_tx,
                "retx":retx,
                "efficiency":f"{efficiency:.1f}%",
                "kbps":f"{kbps:.2f}",
            })
        finally:
            router_proc.terminate()
            recv_proc.terminate()
            router_proc.wait()
            recv_proc.wait()
            time.sleep(0.3)

    print("\n###BENCHMARK RESULTS TABLE\n")
    print(f"| {'Scenario':<21} | {'Time':<7} | {'Total Tx':<8} | {'Retransmits':<11} | {'Efficiency':<10} | {'Throughput':<11} |")
    print(f"|{'-'*23}|{'-'*9}|{'-'*10}|{'-'*13}{'-'*12}{'-'*13}|")
    for r in results:
        print(
            f"| {r['scenario']:21} | {r['elapsed']:<7} | {r['total_tx']:<8} | "
            f"{r['retx']:<11} | {r['efficiency']:<10} | {r['kbps'] + ' kbps':<11} |"
        )

if __name__=="__main__":
    run_benchmark()