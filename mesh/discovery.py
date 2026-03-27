"""
Node Discovery Module

This module handles how nodes find each other on the local network.
We use UDP broadcasting - a node shouts "I'm here!" to everyone on the 
network simultaneously, and any other nodes running the same software
will hear it and respond.

Think of it like walking into a room and saying "Is anyone here?" -
everyone in the room can hear you at once.

UDP vs TCP:
  - TCP: Like a phone call - you establish a connection first, then talk
  - UDP: Like shouting in a room - you send the message without waiting
         for a connection. Faster, but less reliable. Perfect for discovery.
"""

import asyncio
import json
import socket
import time
from loguru import logger



DISCOVERY_PORT = 9000

# How often a node announces itself (in seconds)
ANNOUNCEMENT_INTERVAL = 5


class NodeDiscovery:

    
    def __init__(self, mesh_node):
        
        self.node = mesh_node
        self.is_running = False

    async def start(self):
        
        """Start both broadcasting and listening at the same time."""
        
        self.is_running = True
        logger.info(f" Discovery started for {self.node.node_name}")
        
        # Run both tasks concurrently using asyncio
        # asyncio.gather() runs multiple async functions at the same time
        
        await asyncio.gather(
            self._broadcast_presence(),  # Task 1: Announce ourselves
            self._listen_for_peers()     # Task 2: Listen for others
        )

    async def _broadcast_presence(self):
    
        """
        Repeatedly broadcast this node's info to the entire local network.
        
        UDP broadcast works by sending to the special address 255.255.255.255
        which means "send this to EVERYONE on the local network".
        """
        
        # Create a UDP socket for broadcasting
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # IMPORTANT: This option allows broadcasting
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        logger.info(f"📡 Broadcasting presence every {ANNOUNCEMENT_INTERVAL}s")
        
        while self.is_running:
            try:
                # Prepare our announcement message
                announcement = {
                    "type": "node_announcement",
                    "node_info": self.node.get_node_info(),
                    "timestamp": time.time()
                }
                
                # Convert to bytes (network data is always bytes)
                message_bytes = json.dumps(announcement).encode('utf-8')
                
                # Send to broadcast address on the discovery port
                sock.sendto(message_bytes, ('255.255.255.255', DISCOVERY_PORT))
                
                logger.debug(f"📡 Announced: {self.node.node_name}")
                
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
            
            # Wait before next announcement
            # asyncio.sleep is non-blocking - other tasks can run during this wait
            await asyncio.sleep(ANNOUNCEMENT_INTERVAL)
        
        sock.close()

    async def _listen_for_peers(self):
        """
        Listen for announcements from other nodes on the network.
        
        When we receive an announcement, we register that node as a peer.
        """
        
        # Create a UDP socket for receiving
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # SO_REUSEADDR allows multiple programs to listen on the same port
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to the discovery port on all network interfaces ('0.0.0.0')
        # '0.0.0.0' means "listen on all available network interfaces"
        sock.bind(('0.0.0.0', DISCOVERY_PORT))
        
        # Make the socket non-blocking so asyncio can manage it
        sock.setblocking(False)
        
        logger.info(f" Listening for peers on port {DISCOVERY_PORT}")
        
        loop = asyncio.get_event_loop()
        
        while self.is_running:
            try:
                # recvfrom receives data AND the sender's address
                # 4096 is the max bytes to receive at once
                data, addr = await loop.sock_recvfrom(sock, 4096)
                
                # Decode bytes back to string, then parse JSON
                message = json.loads(data.decode('utf-8'))
                
                if message.get("type") == "node_announcement":
                    peer_info = message.get("node_info", {})
                    
                    # Register this peer with our node
                    self.node.register_peer(peer_info)
                    
            except Exception as e:
                # recvfrom raises an error when no data is available
                # in non-blocking mode — this is normal, just wait and retry
                await asyncio.sleep(0.1)
        
        sock.close()