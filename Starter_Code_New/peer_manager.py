import threading
import time
import json
from collections import defaultdict
from peer_discovery import get_known_peers


peer_status = {} # {peer_id: 'ALIVE', 'UNREACHABLE' or 'UNKNOWN'}
last_ping_time = {} # {peer_id: timestamp}
rtt_tracker = {} # {peer_id: transmission latency}

# === Check if peers are alive ===

def ping_json_gen(message_type,self_id,timestamp):
    return {
        "type": message_type,
        "id": self_id,
        "tt": timestamp
    }


def start_ping_loop(self_id, peer_table):
    from outbox import enqueue_message
    def loop():
       # TODO: Define the JSON format of a `ping` message, which should include `{message typy, sender's ID, timestamp}`.
        #in ping_json_gen function
       # TODO: Send a `ping` message to each known peer periodically.
        while True:
            peers = get_known_peers()
            for peer in peers:
                ping = ping_json_gen("PING", self_id, time.time())
                enqueue_message(peer,peers[peer][0], peers[peer][1], ping)

            time.sleep(5) #？？？
        pass
    threading.Thread(target=loop, daemon=True).start()

def create_pong(sender, recv_ts):
    #recv_ts is the timestamp in the received ping message
    # TODO: Create the JSON format of a `pong` message, which should include `{message type, sender's ID, timestamp in the received ping message}`.
    return {
        "type": "PONG",
        "id": sender, #发pong的人的id  #？？？##？？？
        "tt": recv_ts #timestamp
    }

def handle_pong(msg):
    # TODO: Read the information in the received `pong` message.
    sender_id = msg["id"]
    recv_ts = msg["tt"]
    # TODO: Update the transmission latenty between the peer and the sender (`rtt_tracker`).
    rtt_tracker[sender_id] = time.time() - recv_ts


LIMIT = 10  #？？？
def start_peer_monitor():
    import threading
    def loop():
        # TODO: Check the latest time to receive `ping` or `pong` message from each peer in `last_ping_time`.
        while True:
            # TODO: If the latest time is earlier than the limit, mark the peer's status in `peer_status` as `UNREACHABLE` or otherwise `ALIVE`.
            for peer_id in last_ping_time:
                if time.time() - last_ping_time[peer_id] > LIMIT:
                    peer_status[peer_id] = "UNREACHABLE"
                else:
                    peer_status[peer_id] = "ALIVE"
            time.sleep(1) #??
            # print("peer_status:", peer_status)

    threading.Thread(target=loop, daemon=True).start()

def update_peer_heartbeat(peer_id):
    # TODO: Update the `last_ping_time` of a peer when receiving its `ping` or `pong` message.
    last_ping_time[peer_id] = time.time() #用发的消息里的id ？


# === Blacklist Logic ===

blacklist = set() # The set of banned peers

peer_offense_counts = {} # The offence times of peers

def record_offense(peer_id):
    # TODO: Record the offence times of a peer when malicious behaviors are detected.
    if peer_id not in peer_offense_counts:
        peer_offense_counts[peer_id] = 1
    else:
        peer_offense_counts[peer_id] += 1
    # TODO: Add a peer to `blacklist` if its offence times exceed 3. 
    if peer_offense_counts[peer_id] >= 3:
        blacklist.add(peer_id)

def get_blacklist():
    return blacklist


