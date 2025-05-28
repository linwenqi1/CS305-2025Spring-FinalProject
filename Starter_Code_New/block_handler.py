
import time
import hashlib
import json
import threading
import random
from transaction import get_recent_transactions, clear_pool, TransactionMessage
from peer_discovery import known_peers, peer_config

from outbox import  enqueue_message, gossip_message
from utils import generate_message_id
from peer_manager import record_offense

received_blocks = [] # The local blockchain. The blocks are added linearly at the end of the set.
header_store = [] # The header of blocks in the local blockchain. Used by lightweight peers.
orphan_blocks = {} # The block whose previous block is not in the local blockchain. Waiting for the previous block.
block_ids_in_chain = set()
def request_block_sync(self_id):
    # TODO: Define the JSON format of a `GET_BLOCK_HEADERS`, which should include `{message type, sender's ID}`.
    get_block_headers_msg = {
        "type": "GET_BLOCK_HEADERS",
        "sender_id": self_id
    }
    # TODO: Send a `GET_BLOCK_HEADERS` message to each known peer and put the messages in the outbox queue.
    print(f"[{self_id}] Requesting block headers from known peers", flush=True)
    for peer_id,(ip,port) in known_peers:
        if peer_id != self_id:  # Avoid sending to self
            enqueue_message(peer_id, ip, port, get_block_headers_msg)

    pass

def block_generation(self_id, MALICIOUS_MODE, interval=20):
    from inv_message import create_inv
    def mine():
        while True:
            time.sleep(interval)
            print(f"[{self_id}] Generating a new block...", flush=True)
            block = create_dummy_block(self_id, MALICIOUS_MODE)
    # TODO: Create a new block periodically using the function `create_dummy_block`.

    # TODO: Create an `INV` message for the new block using the function `create_inv` in `inv_message.py`.
            inv_msg = create_inv(self_id, [block.block_id])  
            if inv_msg:
                print(f"[{self_id}] Broadcasting INV for new block {block.block_id[:8]}")
                # gossip_message 的参数可能需要调整
                # gossip_message(sender_id, message_content, message_type)
                gossip_message(self_id, inv_msg)
            else:
                print(f"[{self_id}] Failed to create INV message for block {block.block_id[:8]}")


    # TODO: Broadcast the `INV` message to known peers using the function `gossip` in `outbox.py`.
            pass
    threading.Thread(target=mine, daemon=True).start()


def initialize_blockchain():
    if not received_blocks: 
        genesis_transactions = []
        genesis = Block(peer_id="genesis_node", previous_block_id=None, transactions=genesis_transactions, timestamp=0)
        genesis.block_id = "0000000000000000000000000000000000000000000000000000000000000000"
        received_blocks.append(genesis)
        block_ids_in_chain.add(genesis.block_id)
        print(f"Blockchain initialized with Genesis Block: {genesis.block_id}")

# 在 node.py 的 main 函数早期调用 initialize_blockchain()


class Block:
    def __init__(self, peer_id, previous_block_id, transactions,block_id=None,malicious_mode=False):
        self.type = "BLOCK"
        self.peer_id = peer_id
        self.timestamp = int(time.time())
        self.previous_block_id = previous_block_id
        self.transactions = transactions
        self.malicious_mode = malicious_mode
        if block_id: 
        # 情况1: 从网络接收区块时，block_id 是已知的，直接使用
            self.block_id = block_id
        elif malicious_mode:
            # 情况2: 节点是恶意的，生成一个随机的、无效的 block_id
            self.block_id = hashlib.sha256(str(random.random()).encode()).hexdigest() 
        else:
            # 情况3: 正常创建新区块，计算哈希作为 block_id
            # 此时，所有其他字段 (peer_id, timestamp, previous_block_id, transactions) 都已赋值
            self.block_id = self.compute_hash() 

    def to_dict(self):
        return {
            "type": self.type,
            "peer_id": self.peer_id,
            "timestamp": self.timestamp,
            "block_id": self.block_id,
            "previous_block_id": self.previous_block_id,
            "malicious_mode": self.malicious_mode,
            "transactions": [tx.to_dict() for tx in self.transactions]
        }
    
    def from_dict(data):
        """Creates a Block object from a dictionary (received from network)."""
        transactions_objs = [TransactionMessage.from_dict(tx_data) for tx_data in data.get("transactions", [])]
        return Block(
            peer_id=data["peer_id"],
            previous_block_id=data["previous_block_id"],
            transactions=transactions_objs,
            malicious_mode=data.get("malicious_mode", False),
            timestamp=data["timestamp"],
            block_id=data["block_id"] 
        )
    
    def compute_hash(self):
        block_data = {
            "type": self.type,
            "peer_id": self.peer_id,
            "timestamp": self.timestamp,
            "previous_block_id": self.previous_block_id,
            "transactions": self.transactions,
            "malicious_mode": self.malicious_mode
        }
        return hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()

def add_block_to_chain(block):
    received_blocks.append(block)
    block_ids_in_chain.add(block.block_id)
    print(f"Block {block.block_id} added to the blockchain by {block.peer_id} at {block.timestamp}, clear local transaction pool.")
    process_orphans(block.block_id)

def process_orphans(previous_block_id):
    """Check if there are orphaned blocks that can be added to the blockchain."""
    global orphan_blocks
    orphans_to_process_ids = [orphan_id for orphan_id, orphan_block in orphan_blocks.items() if orphan_block.previous_block_id == previous_block_id]
    for orphan_id in orphans_to_process_ids:
        orphan_block = orphan_blocks.pop(orphan_id)
        add_block_to_chain(orphan_block)
        print(f"Orphan block {orphan_id} added to the blockchain as it follows the previous block {previous_block_id}.")


def create_dummy_block(peer_id, MALICIOUS_MODE):

    # TODO: Define the JSON format of a `block`, which should include `{message type, peer's ID, timestamp, block ID, previous block's ID, 
    # and transactions}`. 
    # The `block ID` is the hash value of block structure except for the item `block ID`. 
    # `previous block` is the last block in the blockchain, to which the new block will be linked. 
    # If the block generator is malicious, it can generate random block ID.

    # TODO: Read the transactions in the local `tx_pool` using the function `get_recent_transactions` in `transaction.py`.
    transactions = get_recent_transactions()
    previous_block_id = received_blocks[-1].block_id if received_blocks else None
    # TODO: Create a new block with the transactions and generate the block ID using the function `compute_block_hash`.
    block = Block(peer_id=peer_id, previous_block_id=previous_block_id, transactions=transactions,malicious_mode=MALICIOUS_MODE)
    # TODO: Clear the local transaction pool and add the new block into the local blockchain (`receive_block`).
    clear_pool()  # Clear the local transaction pool after adding the block
    add_block_to_chain(block)
    pass
    return block

def compute_block_hash(block):
    # TODO: Compute the hash of a block except for the term `block ID`.
    return block.compute_hash()
    pass

def handle_block(msg, self_id):
    # TODO: Check the correctness of `block ID` in the received block. If incorrect, drop the block and record the sender's offence.
    block = Block.from_dict(msg)
    expected_block_id = compute_block_hash(block)
    received_block_id = block.block_id
    if expected_block_id != received_block_id:
        print(f"[{self_id}] Received block with incorrect ID: {received_block_id}, expected: {expected_block_id}. Dropping block and recording offense.")
        record_offense(block.peer_id, "Incorrect block ID")
        return
    # TODO: Check if the block exists in the local blockchain. If yes, drop the block.
    if block.block_id in block_ids_in_chain:
        print(f"[{self_id}] Block {block.block_id} already exists in the blockchain. Dropping duplicate block.")
        return
    # TODO: Check if the previous block of the block exists in the local blockchain. If not, add the block to the list of orphaned blocks (`orphan_blocks`). If yes, add the block to the local blockchain.
    previous_block_id = block.previous_block_id
    if previous_block_id is not None and previous_block_id not in block_ids_in_chain:
        print(f"[{self_id}] Block {block.block_id} is orphaned (previous block {previous_block_id} not found). Adding to orphan blocks.")
        orphan_blocks[block.block_id] = block  # Store the orphaned block
        return
    
    # TODO: Check if the block is the previous block of blocks in `orphan_blocks`. If yes, add the orphaned blocks to the local blockchain.
    add_block_to_chain(block)
    print(f"[{self_id}] Block {block.block_id} added to the blockchain.")
    from inv_message import create_inv
    inv_msg = create_inv(self_id, [block.block_id])
    gossip_message(self_id, inv_msg)  # Broadcast the new block to known peers
    pass


def create_getblock(sender_id, requested_ids):
    return {
        "type": "GETBLOCK",
        "sender_id": sender_id,
        "block_ids": requested_ids
    }


def get_block_by_id(block_id):
    block = block_ids_in_chain.get(block_id)
    if block:
        return block
    else:
        print(f"Block {block_id} not found in the local blockchain.")
        return None
