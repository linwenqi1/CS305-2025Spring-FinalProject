import json, time, threading, random
from utils import generate_message_id


known_peers = {}        # { peer_id: (ip, port) }
peer_flags = {}         # { peer_id: { 'nat': True/False, 'light': True/False } }
reachable_by = {}       # { peer_id: { set of peer_ids who can reach this peer }}
peer_config={}

def get_known_peers():
    return known_peers

def hello_json_gen(message_type,self_id,self_ip,self_port,flags,message_id):
    #sender_port <=> sender_ID
    return {
        "type": message_type,
        "id": self_id,
        "ip": self_ip,
        "port": self_port,
        "flags": flags, #a boolean tuple (isNAT,isfull)
        "m_id": message_id
    }

def start_peer_discovery(self_id, self_info):
    from outbox import enqueue_message
    def loop():
        #time.sleep(1) #??需要sleep吗
        # TODO: Define the JSON format of a `hello` message, which should include: `{message type, sender’s ID, IP address, port, flags, and message ID}`. 
        # A `sender’s ID` can be `peer_port`. 
        # The `flags` should indicate whether the peer is `NATed or non-NATed`, and `full or lightweight`. 
        # The `message ID` can be a random number.
        hello = hello_json_gen(message_type="HELLO",
                               self_id=self_id,
                               self_ip=self_info["ip"],
                               self_port=self_info["port"],
                               flags= peer_flags[self_id],
                               message_id=random.randint(0,1000000)
                               )



        # TODO: Send a `hello` message to all known peers and put the messages into the outbox queue.
        for peer_id in known_peers:
            enqueue_message(peer_id, known_peers[peer_id][0], known_peers[peer_id][1], hello)
    threading.Thread(target=loop, daemon=True).start()

def handle_hello_message(msg, self_id):
    new_peers = None

    # TODO: Read information in the received `hello` message.
    sender_id = msg["id"]
    sender_ip = msg["ip"]
    sender_port = msg["port"]
    flags = msg["flags"]
    message_id = msg["m_id"]

    # TODO: If the sender is unknown, add it to the list of known peers (`known_peer`) and record their flags (`peer_flags`).
    if sender_id not in known_peers:
        known_peers[sender_id] = (sender_ip, sender_port)
        peer_flags[sender_id] = flags
        new_peers = sender_id

    # TODO: Update the set of reachable peers (`reachable_by`).
    if sender_id not in reachable_by:
        reachable_by[sender_id] = set()

    if self_id not in reachable_by:
        reachable_by[self_id] = set()

    reachable_by[self_id].add(sender_id)
    reachable_by[sender_id].add(self_id)

    return new_peers #如果发hello的peer是unknown peer,就返回它的id


