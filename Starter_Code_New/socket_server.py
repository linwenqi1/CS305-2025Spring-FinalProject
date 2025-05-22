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
                threading.Thread(target=recv_message(conn,self_id,self_ip), daemon=True).start()
            except Exception as e:
                print(f"[ERROR] Failed to accept connection: {e}")

    # ✅ Run listener in background
    threading.Thread(target=listen_loop, daemon=True).start()


def recv_message(conn,self_id,self_ip):
    while True:
        json_obj = recv_json(conn)
        dispatch_message(json_obj, self_id, self_ip)

import struct
def recv_json(sock):
    """
    从socket连接接收JSON对象
    :param sock: 已建立的socket连接
    :return: 反序列化后的Python对象
    """
    # 先接收4字节的长度信息
    length_data = recv_all(sock, 4)
    if not length_data:
        return None

    # 解析数据长度
    length = struct.unpack('!I', length_data)[0]

    # 接收JSON数据
    json_bytes = recv_all(sock, length)
    if not json_bytes:
        return None

    # 反序列化为Python对象
    return json.loads(json_bytes.decode('utf-8'))

def recv_all(sock, n):
    """
    确保接收指定数量的字节
    :param sock: socket连接
    :param n: 要接收的字节数
    :return: 接收到的字节数据
    """
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data