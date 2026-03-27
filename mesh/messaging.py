"""
mesh/messaging.py

Handles sending and receiving messages between mesh nodes.
Uses TCP (not UDP) for message delivery because unlike discovery,
messages must be delivered reliably and in order.

UDP = fire and forget (good for announcements)
TCP = confirmed delivery (good for actual messages)

Each node runs a TCP server that listens for incoming messages.
When a message arrives, the node decides to:
  - Deliver it (if addressed to self or broadcast)
  - Relay it (forward to all peers with hop_count + 1)
  - Drop it (if already seen or hop limit reached)
"""

import asyncio
import json
import time
from loguru import logger


class MeshMessenger:
    """
    Manages message sending, receiving, and relaying for a mesh node.
    """

    def __init__(self, mesh_node):
        """
        Args:
            mesh_node: The MeshNode instance this messenger belongs to
        """
        self.node = mesh_node
        self.server = None
        self.received_messages = []  # Store delivered messages for display
        self.on_message_received = None  # Optional callback when message arrives

    async def start_server(self):
        """
        Start the TCP server that listens for incoming messages.
        
        asyncio.start_server creates a server that calls handle_connection
        every time a new device connects to us.
        """
        self.server = await asyncio.start_server(
            self._handle_connection,
            '0.0.0.0',       # Listen on all network interfaces
            self.node.port,  # Use this node's assigned port
        )
        logger.info(f"Message server listening on port {self.node.port}")

    async def _handle_connection(self, reader, writer):
        """
        Called automatically when another node connects to us.
        
        reader: used to receive data
        writer: used to send data back
        """
        try:
            # Read incoming data (up to 65535 bytes)
            data = await reader.read(65535)
            if not data:
                return

            message = json.loads(data.decode('utf-8'))
            await self._process_message(message)

        except Exception as e:
            logger.error(f"Connection handler error: {e}")
        finally:
            writer.close()

    async def _process_message(self, message: dict):
        """
        Decide what to do with a received message.
        
        Three possible outcomes:
        1. Deliver to self (message is for us or is a broadcast)
        2. Relay to peers (message is for someone else, we forward it)
        3. Drop (already seen, or hop limit reached)
        """
        message_id = message.get("message_id")
        recipient_id = message.get("recipient_id")

        # Check relay rules defined in node.py
        if not self.node.should_relay(message):
            return

        # Mark as seen to prevent processing it again
        self.node.mark_seen(message_id)

        # Deliver if addressed to us or it is a broadcast
        if recipient_id == self.node.node_id or recipient_id == "broadcast":
            self._deliver_message(message)

        # Relay if not addressed exclusively to us
        if recipient_id != self.node.node_id:
            await self._relay_message(message)

    def _deliver_message(self, message: dict):
        """
        Accept a message as delivered to this node.
        Store it and trigger callback if one is registered.
        """
        self.received_messages.append(message)

        sender = message.get("sender_name", "unknown")
        content = message.get("content", "")
        hops = message.get("hop_count", 0)

        print(f"\n[Message received] From: {sender} | Hops: {hops}")
        print(f"  > {content}\n")

        # If a callback is registered, call it (useful for the Flutter app later)
        if self.on_message_received:
            self.on_message_received(message)

    async def _relay_message(self, message: dict):
        """
        Forward a message to all known peers.
        
        Before forwarding we increment the hop count.
        This lets receivers know how many nodes the message passed through.
        """
        # Increment hop count
        relayed = dict(message)
        relayed["hop_count"] = message.get("hop_count", 0) + 1
        relayed["relay_path"] = message.get("relay_path", []) + [self.node.node_id]

        logger.debug(f"Relaying message {message.get('message_id', '')[:8]} | hop {relayed['hop_count']}")
        await self._broadcast_to_peers(relayed)

    async def send_message(self, content: str, recipient_id: str = "broadcast"):
        """
        Send a message from this node to the network.
        
        Args:
            content: The text to send
            recipient_id: Target node ID, or 'broadcast' for everyone
        """
        message = self.node.create_message(content, recipient_id)

        # Mark our own message as seen so we don't relay it back
        self.node.mark_seen(message["message_id"])

        await self._broadcast_to_peers(message)
        logger.info(f"Message sent: '{content[:40]}' -> {recipient_id}")
        return message

    async def _broadcast_to_peers(self, message: dict):
        """
        Send a message to all known peers simultaneously.
        
        asyncio.gather sends to all peers concurrently rather than
        waiting for each one to finish before trying the next.
        """
        if not self.node.peers:
            logger.warning("No peers to send to")
            return

        tasks = [
            self._send_to_peer(peer_info, message)
            for peer_info in self.node.peers.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_peer(self, peer_info: dict, message: dict):
        """
        Open a TCP connection to a specific peer and send the message.
        
        Args:
            peer_info: Dictionary with host and port of target peer
            message: The message dictionary to send
        """
        host = peer_info.get("host")
        port = peer_info.get("port")

        try:
            # asyncio.open_connection creates a TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0  # Give up after 5 seconds if no response
            )

            data = json.dumps(message).encode('utf-8')
            writer.write(data)
            await writer.drain()  # Make sure all data is sent
            writer.close()

        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending to {peer_info.get('node_name')} @ {host}:{port}")
        except ConnectionRefusedError:
            logger.warning(f"Connection refused by {peer_info.get('node_name')} @ {host}:{port}")
        except Exception as e:
            logger.error(f"Send error to {host}:{port} -> {e}")
