import socket
import threading
import time
import json
import random
from collections import defaultdict, deque
from threading import Lock

# === Per-peer Rate Limiting ===
RATE_LIMIT = 10  # max messages
TIME_WINDOW = 10  # per seconds
peer_send_timestamps = defaultdict(list) # the timestamps of sending messages to each peer

MAX_RETRIES = 3
RETRY_INTERVAL = 5  # seconds
QUEUE_LIMIT = 50

# Priority levels
PRIORITY_HIGH = {"PING", "PONG", "BLOCK", "INV", "GETDATA"}
PRIORITY_MEDIUM = {"TX", "HELLO"}
PRIORITY_LOW = {"RELAY"}

DROP_PROB = 0.05
LATENCY_MS = (20, 100)
SEND_RATE_LIMIT = 5  # messages per second

drop_stats = {
    "BLOCK": 0,
    "TX": 0,
    "HELLO": 0,
    "PING": 0,
    "PONG": 0,
    "OTHER": 0
}

priority_order = {
    "BLOCK": 1,
    "TX": 2,
    "PING": 3,
    "PONG": 4,
    "HELLO": 5
}

# Queues per peer and priority
queues = defaultdict(lambda: defaultdict(deque))
retries = defaultdict(int)
lock = threading.Lock()

# === Sending Rate Limiter ===
class RateLimiter:
    def __init__(self, rate=SEND_RATE_LIMIT):
        self.capacity = rate               # Max burst size
        self.tokens = rate                # Start full
        self.refill_rate = rate           # Tokens added per second
        self.last_check = time.time()
        self.lock = Lock()

    def allow(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_check
            self.tokens += elapsed * self.refill_rate
            self.tokens = min(self.tokens, self.capacity)
            self.last_check = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

rate_limiter = RateLimiter()

def enqueue_message(target_id, ip, port, message):
    from peer_manager import blacklist, rtt_tracker
    
    # TODO: Check if the peer sends message to the receiver too frequently using the function `is_rate_limited`. If yes, drop the message.
    
    # Get the message type
    msg_type = message.get("type")
    if msg_type == "HELLO":
        print(f"[INFO] HELLO is add to the queue")
    if msg_type not in drop_stats:
        msg_type = "OTHER"  # ???
    if is_rate_limited(target_id):
        drop_stats[msg_type] += 1
        return
    # TODO: Check if the receiver exists in the `blacklist`. If yes, drop the message.
    if target_id in blacklist:
        drop_stats[msg_type] += 1
        return
    # TODO: Classify the priority of the sending messages based on the message type using the function `classify_priority`.
    priority = classify_priority(message)
    # TODO: Add the message to the queue (`queues`) if the length of the queue is within the limit `QUEUE_LIMIT`, or otherwise, drop the message.
    with lock:
        if len(queues[target_id][priority]) < QUEUE_LIMIT:
            queues[target_id][priority].append(message)
        else:
            drop_stats[msg_type] += 1
            return
    # pass


def is_rate_limited(peer_id):
    # TODO:Check how many messages were sent from the peer to a target peer during the `TIME_WINDOW` that ends now.
    now = time.time()
    timestamps = [t for t in peer_send_timestamps[peer_id] if now - t < TIME_WINDOW]
    peer_send_timestamps[peer_id] = timestamps
    if len(timestamps) >= RATE_LIMIT:
        return True
    peer_send_timestamps[peer_id].append(now)
    return False
    # TODO: If the sending frequency exceeds the sending rate limit `RATE_LIMIT`, return `TRUE`; otherwise, record the current sending time into `peer_send_timestamps`.
    # pass

def classify_priority(message):
    # TODO: Classify the priority of a message based on the message type.
    msg_type = message.get("type")
    if msg_type in PRIORITY_HIGH:
        return "high"
    elif msg_type in PRIORITY_MEDIUM:
        return "medium"
    elif msg_type in PRIORITY_LOW:
        return "low"
    else:
        return "low" #???
    # pass


import struct

def send_json(sock, json_obj):
    """
    发送JSON对象到socket连接
    :param sock: 已建立的socket连接
    :param json_obj: 要发送的Python对象(可序列化为JSON)
    """
    # 将对象序列化为JSON字符串
    json_str = json.dumps(json_obj)
    # 转换为字节流
    json_bytes = json_str.encode('utf-8')

    # 先发送数据长度(4字节网络字节序)
    sock.sendall(struct.pack('!I', len(json_bytes)) + json_bytes)
    # 发送实际数据
    # sock.sendall(json_bytes)

def send_from_queue(self_id):
    def worker():
        # TODO: Read the message in the queue. Each time, read one message with the highest priority of a target peer. After sending the message, read the message of the next target peer. This ensures the fairness of sending messages to different target peers.
        while True:
            peer_ids = list(queues.keys())
            if not peer_ids:
                # time.sleep(0.1) # ???
                continue
            for target_id in peer_ids:
                message = None
                for priority in ["high", "medium", "low"]:
                    with lock:
                        if queues[target_id][priority]:
                            message = queues[target_id][priority].popleft()
                            break
                if message is None:
                    continue
                retry_count = 0
                while retry_count < MAX_RETRIES: # send the message
                    success = relay_or_direct_send(self_id, target_id, message)
                    if success:
                        break
                    retry_count += 1  # increment retry count
                    time.sleep(RETRY_INTERVAL)
                if retry_count >= MAX_RETRIES: # drop the message
                    msg_type = message.get("type")
                    if msg_type not in drop_stats:
                        msg_type = "OTHER"
                    drop_stats[msg_type] += 1
            # time.sleep(0.1)  # Sleep for a short time to avoid busy waiting
                    
        # TODO: Send the message using the function `relay_or_direct_send`, which will decide whether to send the message to target peer directly or through a relaying peer.

        # TODO: Retry a message if it is sent unsuccessfully and drop the message if the retry times exceed the limit `MAX_RETRIES`.

        # pass
    threading.Thread(target=worker, daemon=True).start()

def relay_or_direct_send(self_id, dst_id, message):
    from peer_discovery import known_peers, peer_flags

    # TODO: Check if the target peer is NATed. 
    # is_nated = peer_flags[dst_id].get("nat", False)

    # TODO: If the target peer is NATed, use the function `get_relay_peer` to find the best relaying peer. 
    # Define the JSON format of a `RELAY` message, which should include `{message type, sender's ID, target peer's ID, `payload`}`. 
    # `payload` is the sending message. 
    # Send the `RELAY` message to the best relaying peer using the function `send_message`.
    is_nated = False
    if is_nated:
        relay_peer = get_relay_peer(self_id, dst_id)
        if relay_peer is not None:
            relay_message = {
                "type": "RELAY",
                "sender": self_id,
                "target": dst_id,
                "payload": message
            }
            return send_message(relay_peer[1], relay_peer[2], relay_message)
        else:
            # No relaying peer found, drop the message
            drop_stats[message.get("type", "OTHER")] += 1
            return False
    # TODO: If the target peer is non-NATed, send the message to the target peer using the function `send_message`.
    else:
        return send_message(known_peers[dst_id][0], known_peers[dst_id][1], message)
    # pass

def get_relay_peer(self_id, dst_id):
    from peer_manager import  rtt_tracker
    from peer_discovery import known_peers, reachable_by

    # TODO: Find the set of relay candidates reachable from the target peer in `reachable_by` of `peer_discovery.py`.
    reachable_by_set = reachable_by.get(dst_id, set())
    # TODO: Read the transmission latency between the sender and other peers in `rtt_tracker` in `peer_manager.py`.
    rtt_tracker_set = {peer_id: rtt for peer_id, rtt in rtt_tracker.items() if peer_id != self_id and peer_id in reachable_by_set}
    # TODO: Select and return the best relaying peer with the smallest transmission latency.
    best_peer = None
    min_rtt = float('inf')
    for peer_id, rtt in rtt_tracker_set.items():
        if rtt < min_rtt:
            min_rtt = rtt
            best_peer = (peer_id, known_peers[peer_id][0], known_peers[peer_id][1])
    # pass

    return best_peer  # (peer_id, ip, port) or None

def send_message(ip, port, message):

    # TODO: Send the message to the target peer. 
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, port))
            send_json(sock, message)
        print(f"[INFO] Sent message to {ip}:{port} - {message}")
        return True
    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused to {ip}:{port}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send message to {ip}:{port} - {e}")
        return False
    # Wrap the function `send_message` with the dynamic network condition in the function `apply_network_condition` of `link_simulator.py`.
    # pass

# send_message = apply_network_conditions(send_message)

def apply_network_conditions(send_func):
    def wrapper(ip, port, message):

        # TODO: Use the function `rate_limiter.allow` to check if the peer's sending rate is out of limit. 
        # If yes, drop the message and update the drop states (`drop_stats`).
        if not rate_limiter.allow():
            msg_type = message.get("type", "OTHER")
            drop_stats[msg_type] += 1
            return False
        # TODO: Generate a random number. If it is smaller than `DROP_PROB`, drop the message to simulate the random message drop in the channel. 
        # Update the drop states (`drop_stats`).
        if random.random() < DROP_PROB:
            msg_type = message.get("type", "OTHER")
            drop_stats[msg_type] += 1
            return False
        # TODO: Add a random latency before sending the message to simulate message transmission delay.
        latency = random.randint(LATENCY_MS[0], LATENCY_MS[1]) / 1000.0
        time.sleep(latency)
        # TODO: Send the message using the function `send_func`.
        return send_func(ip, port, message)
        # pass
    return wrapper

def start_dynamic_capacity_adjustment():
    def adjust_loop():
        # TODO: Peridically change the peer's sending capacity in `rate_limiter` within the range [2, 10].
        pass
    threading.Thread(target=adjust_loop, daemon=True).start()


def gossip_message(self_id, message, fanout=3):

    from peer_discovery import known_peers, peer_config

    # TODO: Read the configuration `fanout` of the peer in `peer_config` of `peer_discovery.py`.

    # TODO: Randomly select the number of target peer from `known_peers`, which is equal to `fanout`. If the gossip message is a transaction, skip the lightweight peers in the `know_peers`.

    # TODO: Send the message to the selected target peer and put them in the outbox queue.
    pass

def get_outbox_status():
    # TODO: Return the message in the outbox queue.
    status = {}
    for peer_id, priority_queues in queues.items():
        status[peer_id] = {priority: list(queue) for priority, queue in priority_queues.items()}
    return status
    # pass


def get_drop_stats():
    # TODO: Return the drop states (`drop_stats`).
    return drop_stats
    # pass

