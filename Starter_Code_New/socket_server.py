import socket
import threading
import time
import json
from message_handler import dispatch_message

RECV_BUFFER = 4096

def start_socket_server(self_id, self_ip, port):

    def listen_loop():
        # TODO: Create a TCP socket and bind it to the peer’s IP address and port.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self_ip, port))

        # TODO: Start listening on the socket for receiving incoming messages.
        sock.listen()
        print(f"[INFO] Peer {self_id} listening on {self_ip}:{port}")
        # TODO: When receiving messages, pass the messages to the function `dispatch_message` in `message_handler.py`.
        while True:
            try:
                conn, addr = sock.accept()
                dispatch_message(conn,self_id,self_ip)
            except Exception as e:
                print(f"[ERROR] Failed to accept connection: {e}")

    # ✅ Run listener in background
    threading.Thread(target=listen_loop, daemon=True).start()