"""
mesh/messaging.py

Handles sending and receiving messages between mesh nodes.
Now supports both text messages and file transfer messages.

Message types:
    text        - plain text chat message (default)
    file_header - metadata about an incoming file transfer
    file_chunk  - one piece of a file being transferred
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
        self.node = mesh_node
        self.server = None
        self.received_messages = []
        self.on_message_received = None

        # FileTransfer instance is injected after creation
        # We do it this way to avoid circular imports
        self.file_transfer = None

    async def start_server(self):
        """Start the TCP server that listens for incoming messages."""
        self.server = await asyncio.start_server(
            self._handle_connection,
            '0.0.0.0',
            self.node.port,
        )
        logger.info(f"Message server listening on port {self.node.port}")

    async def _handle_connection(self, reader, writer):
        """Called automatically when another node connects to us."""
        try:
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

        Handles three message types:
            text        - deliver and relay as before
            file_header - pass to file transfer module
            file_chunk  - pass to file transfer module
        """
        message_id = message.get("message_id")
        recipient_id = message.get("recipient_id")
        msg_type = message.get("type", "text")

        if not self.node.should_relay(message):
            return

        self.node.mark_seen(message_id)

        # Route to correct handler based on message type
        if msg_type in ("file_header", "file_chunk"):
            # Hand off to file transfer module if available
            if self.file_transfer:
                self.file_transfer.handle_incoming(message)
            # Relay file messages across the mesh as well
            if recipient_id != self.node.node_id:
                await self._relay_message(message)

        else:
            # Plain text message
            if recipient_id == self.node.node_id or recipient_id == "broadcast":
                self._deliver_message(message)
            if recipient_id != self.node.node_id:
                await self._relay_message(message)

    def _deliver_message(self, message: dict):
        """Accept and display a text message addressed to this node."""
        self.received_messages.append(message)
        sender = message.get("sender_name", "unknown")
        content = message.get("content", "")
        hops = message.get("hop_count", 0)
        print(f"\n[Message] From: {sender} | Hops: {hops}")
        print(f"  > {content}\n")
        if self.on_message_received:
            self.on_message_received(message)

    async def _relay_message(self, message: dict):
        """Forward a message to all peers with incremented hop count."""
        relayed = dict(message)
        relayed["hop_count"] = message.get("hop_count", 0) + 1
        relayed["relay_path"] = message.get("relay_path", []) + [self.node.node_id]
        logger.debug(f"Relaying message {message.get('message_id','')[:8]} hop {relayed['hop_count']}")
        await self._broadcast_to_peers(relayed)

    async def send_message(self, content: str, recipient_id: str = "broadcast"):
        """Send a plain text message from this node."""
        message = self.node.create_message(content, recipient_id)
        self.node.mark_seen(message["message_id"])
        await self._broadcast_to_peers(message)
        logger.info(f"Message sent: '{content[:40]}'")
        return message

    async def _broadcast_to_peers(self, message: dict):
        """Send a message to all known peers simultaneously."""
        if not self.node.peers:
            logger.warning("No peers to send to")
            return
        tasks = [
            self._send_to_peer(peer_info, message)
            for peer_info in self.node.peers.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_peer(self, peer_info: dict, message: dict):
        """Open a TCP connection to a peer and deliver the message."""
        host = peer_info.get("host")
        port = peer_info.get("port")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            data = json.dumps(message).encode('utf-8')
            writer.write(data)
            await writer.drain()
            writer.close()
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending to {peer_info.get('node_name')} @ {host}:{port}")
        except ConnectionRefusedError:
            logger.warning(f"Connection refused by {peer_info.get('node_name')} @ {host}:{port}")
        except Exception as e:
            logger.error(f"Send error to {host}:{port} -> {e}")
