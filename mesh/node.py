"""
The core Node class for the Decentralized Mesh Network.

Each node represents a single device participating in the network.
A node can:
  - Generate its own unique identity (cryptographic key pair)
  - Announce its presence to the local network
  - Discover other nearby nodes
  - Send and receive messages
  - Relay messages on behalf of other nodes (multi-hop)

Author: Ahmad Muhammad Danrangi
Project: Decentralized Mesh-AI Blockchain Network
Phase: 1 - Mesh Networking Core
"""

import asyncio          # Python's built-in library for async (non-blocking) operations
import socket           # For getting the device's IP address
import json             # For converting data to/from text format (JSON)
import uuid             # For generating unique IDs
import time             # For timestamps
from loguru import logger  # A better version of Python's print() for logging


class MeshNode:
    """
    Represents a single device (node) in the mesh network.
    
    Think of this class as the 'brain' of each device.
    Every phone or laptop running this software becomes a node.
    """

    def __init__(self, node_name: str = None, port: int = 8765):
        """
        Initialize a new mesh node.
        
        Args:
            node_name: A human-readable name (e.g. "node-alice")
                       If not provided, one is generated automatically
            port: The network port this node listens on (like a door number)
                  Default is 8765
        """
        
        # --- Identity ---
        # Every node gets a universally unique ID (UUID)
        # This is like a passport number - no two nodes will ever have the same one
        self.node_id = str(uuid.uuid4())
        
        # Human-readable name for easier debugging
        self.node_name = node_name or f"node-{self.node_id[:8]}"
        
        # --- Network Address ---
        # Get this device's IP address on the local network
        # This is how other nodes will find and connect to us
        self.host = self._get_local_ip()
        self.port = port
        
        # --- Peer Registry ---
        # A dictionary of all known neighboring nodes
        # Format: { node_id: { "host": "192.168.1.5", "port": 8765, "name": "node-bob" } }
        self.peers = {}
        
        # --- Message History ---
        # Keeps track of messages we've already seen
        # This prevents the same message from looping forever in the network
        self.seen_messages = set()
        
        # --- Node State ---
        self.is_running = False
        self.start_time = time.time()
        
        logger.info(f"🟢 Node created: {self.node_name} | ID: {self.node_id[:8]}... | Address: {self.host}:{self.port}")

    def _get_local_ip(self) -> str:
        """
        Automatically detect this device's local IP address.
        
        The trick: we connect to an external address (doesn't actually send data)
        just to find out which network interface (and therefore IP) we'd use.
        """
        try:
            # Create a temporary socket (communication endpoint)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to Google's DNS server (we don't actually send anything)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]  # Read back what IP we used
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"  # Fallback to localhost if detection fails

    def get_node_info(self) -> dict:
        """
        Returns a dictionary of this node's public information.
        This is what we broadcast to other nodes so they can find us.
        """
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "host": self.host,
            "port": self.port,
            "peer_count": len(self.peers),
            "uptime": round(time.time() - self.start_time, 2)
        }

    def register_peer(self, peer_info: dict):
        """
        Add a new node to our list of known peers.
        
        Args:
            peer_info: Dictionary with the peer's id, name, host, port
        """
        peer_id = peer_info.get("node_id")
        
        # Don't add ourselves as a peer
        if peer_id == self.node_id:
            return
            
        # Don't add duplicates
        if peer_id not in self.peers:
            self.peers[peer_id] = peer_info
            logger.info(f"✅ New peer registered: {peer_info.get('node_name')} @ {peer_info.get('host')}:{peer_info.get('port')}")
        
    def create_message(self, content: str, recipient_id: str = "broadcast") -> dict:
        """
        Create a properly formatted mesh network message.
        
        Every message in the network has the same structure so all nodes
        can understand and process it correctly.
        
        Args:
            content: The text content of the message
            recipient_id: Who to send to. "broadcast" means send to everyone.
        
        Returns:
            A dictionary representing the message
        """
        message = {
            "message_id": str(uuid.uuid4()),   # Unique ID to prevent duplicates
            "sender_id": self.node_id,          # Who sent this
            "sender_name": self.node_name,      # Human readable sender name
            "recipient_id": recipient_id,        # Who should receive this
            "content": content,                  # The actual message text
            "timestamp": time.time(),            # When it was sent
            "hop_count": 0,                      # How many nodes it has passed through
            "max_hops": 10                       # Maximum hops before message is dropped
        }
        return message

    def should_relay(self, message: dict) -> bool:
        """
        Decide whether this node should relay (forward) a message.
        
        Rules:
        1. Don't relay messages we've already seen (prevents infinite loops)
        2. Don't relay messages that have exceeded max hops
        3. Don't relay our own messages (we already sent them)
        
        This is a fundamental concept in mesh networking called
        'flooding with duplicate suppression'
        
        Args:
            message: The message dictionary to evaluate
            
        Returns:
            True if we should relay, False if we should drop it
        """
        message_id = message.get("message_id")
        
        # Check if we've seen this message before
        if message_id in self.seen_messages:
            return False
        
        # Check hop count limit
        if message.get("hop_count", 0) >= message.get("max_hops", 10):
            logger.warning(f"⚠️ Message {message_id[:8]}... dropped: max hops reached")
            return False
        
        # Check if we sent this message originally
        if message.get("sender_id") == self.node_id:
            return False
            
        return True

    def mark_seen(self, message_id: str):
        """Mark a message as seen so we don't process it again."""
        self.seen_messages.add(message_id)
        
        # Keep the seen_messages set from growing forever
        # If it gets too large, remove the oldest entries
        if len(self.seen_messages) > 1000:
            # Convert to list, remove first 100, convert back to set
            seen_list = list(self.seen_messages)
            self.seen_messages = set(seen_list[100:])

    def __repr__(self):
        return f"MeshNode(name={self.node_name}, peers={len(self.peers)}, address={self.host}:{self.port})"