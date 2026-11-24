import socket
import time
#TARGET DESTINATION CONFIGURATION
#Must match the IP address and port where receiver.py is actively listening.
DEST_HOST = '127.0.0.1'
DEST_PORT = 65432

#SOCKET CREATION:
#Creates an IPv4(AF_INET) TCP(SOCK_STREAM) endpoint on the client side.
#No calling of bind since the linux kernel automatically assigns a free ephemeral source port(e.g 51422) when connect() is called.
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:

    #INITIATING THE CONNECTION(TCP 3-WAY HANDSHAKE)
    #Sends a TCP SYN PACKET to 127.0.0.1:65432. If receiver.py is not running, the OS rejects it and python raises a ConnectionRefusedError.
    client_socket.connect(( DEST_HOST , DEST_PORT ))

    #getsockname() reveals the local IP and random ephemeral port assigned by wsl in this case.
    local_ip, local_port =client_socket.getsockname()
    print(f"[SENDER] Connected! Local endpoint {local_ip}:{local_port} -> Remote {DEST_HOST}:{DEST_PORT}")

    #DATA TRANSMISSION LOOP
    for packet_num in range(1,6):
        #Construct an application-layer message string.
        message=f"Packet #{packet_num}: Hello Masudi's Network!"

        #.encode('utf-8') serializes the string into a byte sequence.
        payload=message.encode('utf-8')

        #Push the bytes into the TCP stream toward the receiver.
        client_socket.sendall(payload)
        print(f"[SENDER] transmitted ({len(payload)}bytes): {message}")

        #WAITING FOR RESPONSE(BLOCKING CALL)
        #Pauses execution until bytes arrive back from the receiver.(upto 1024 bytes)
        ack_data= client_socket.recv(1024)
        print(f"[SENDER] Server replied: {ack_data.decode('utf-8')}\n")

        #Pause one second between packets so as to inspect the packets in real time.
        time.sleep(1)

    #CONNECTION TEARDOWN
    #Exiting the 'with' block automatically triggers a TCP FIN packet to gracefully close the connection and release the release the ephemeral port back to the os.
    print("[SENDER] Transmission complete. Socket closed.")