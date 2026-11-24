import socket

#NETWORK ADDRESSING CONFIGURATION:
#'127.0.0.1' is the IPv4 loopback address( local host). Traffic stays entirely within the WSL virtual network interface('lo')  and never hits my physical NIC.
HOST = '127.0.0.1'
#Ports 0-1023 are  "well-known" priviledged ports( require root/sudo).
#Ports 1024-49151 are registered ports; 49152-65535 are ephemeral/dynamic ports.
#My choice of 65432 avoids permission errors and conflicts with common background services.
PORT=65432

#SOCKET CREATION:
#AF_INET -> Address family: IPv4 (32-bit addresses like 127.0.0.1)
#SOCK_STREAM-> Socket type: TCP (Connection oriented, reliable , ordered byte stream.)
#The 'with' statement ensures the OS automatically closes the socket and frees the port on exit.
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

	#SOCKET OPTIONS:
	#When a TCP connection closes, the OS places the port in a TIME_WAIT state for  about 60 seconds to catch stray delayed packets.
	#SO_REUSEADDR lets me restart receiver.py immediately.(Without hitting an  "Address already in use" error.
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	#BINDING:
	#Associates this socket object with a specific network interface (HOST) & (PORT) From this point, the linux kernel routes any packets destined for 
	#127.0.0.1:65432 here.
	server_socket.bind ((HOST,PORT))

	#LISTENING:
	#Transitions the socket from CLOSED to LISTEN state, telling the OS kernel to start  queueing incoming TCP SYN (connection) requests.
	server_socket.listen()
	print(f"[RECEIVER] Listening for incoming TCP connections on {HOST}:{PORT}...")

	#ACCEPTING A CONNECTION (BLOCKING CALL)
	#Executions pauses here until a sender completes the TCP 3-way handshake( SYN -> SYN-ACK -> ACK )
	#accept() return a NEW socket object  ('conn') dedicated solely to this specific client,plus a tuple ('addr') containing the client's IP and ephemeral source port.
	conn, addr = server_socket.accept()

	#MANAGE THE DEDICATED CLIENT CONNECTION SOCKET
	with conn:
		print(f"[RECEIVER] 3-way handshake complete! Connected by {addr}")
		while True:
			#RECEIVING DATA (BLOCKING CALL)
			#Reads upto 1024 bytes from the kernel's receive buffer for this connection.
			#Data arrives as raw bytes, not strings.
			data=conn.recv(1024)

			#If recv() return an empty bytes object (b''), the  sender closed its side of the connection (sent a TCP FIN packet).
			if not data:
				print("[RECEIVER] Sender closed the connection (FIN received).")
				break
			#Decode the raw UTF-8 bytes back into a  human-readable python string.
			decoded_message= data.decode('utf-8')
			print(f"[RECEIVER] Received payload ({len(data)} bytess): {decoded_message}")
			
			#SENDING APPLICATION-LEVEL RESPONSE
			#Echo an acknowledgment message back through the established TCP stream.
			#sendall() ensures all bytes are transmitted even if the network buffer is busy.
			response=f"ACK: {decoded_message}".encode('utf-8')
			conn.sendall(response)
