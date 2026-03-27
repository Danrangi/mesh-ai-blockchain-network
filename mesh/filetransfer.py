"""
mesh/filetransfer.py

Handles sending and receiving files across the mesh network.

Files are broken into chunks, sent individually, and reassembled
on the receiver's side. A checksum verifies the file arrived intact.

Key concepts:
    Chunking   - splitting a large file into smaller pieces
    Checksum   - a fingerprint to verify file integrity (MD5)
    Reassembly - putting chunks back together in the correct order
    Progress   - tracking how many chunks have arrived
"""

import asyncio
import json
import os
import math
import hashlib
import base64
import time
import uuid
from loguru import logger


# Maximum size of each chunk in bytes (512 KB)
CHUNK_SIZE = 512 * 1024

# Directory where received files are saved
RECEIVED_FILES_DIR = os.path.join(os.path.dirname(__file__), "received_files")


def compute_checksum(file_path: str) -> str:
    """
    Compute the MD5 checksum of a file.

    MD5 reads the entire file and produces a short fixed-length string
    that acts as a fingerprint. If the file changes even slightly,
    the fingerprint changes completely.

    Args:
        file_path: Path to the file on disk

    Returns:
        MD5 hex string e.g. "d41d8cd98f00b204e9800998ecf8427e"
    """
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read in blocks to avoid loading huge files into memory at once
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def split_file_into_chunks(file_path: str) -> list:
    """
    Read a file from disk and split it into base64-encoded chunks.

    We use base64 encoding because our messaging system sends JSON,
    and JSON cannot contain raw binary data. Base64 converts binary
    to plain text safely.

    Args:
        file_path: Path to the file to split

    Returns:
        List of base64-encoded strings, one per chunk
    """
    chunks = []
    with open(file_path, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            # Encode binary data as base64 string
            encoded = base64.b64encode(data).decode("utf-8")
            chunks.append(encoded)
    return chunks


class FileTransfer:
    """
    Manages outgoing and incoming file transfers for a mesh node.

    Outgoing: splits file, creates transfer session, sends chunks
    Incoming: collects chunks, tracks progress, reassembles file
    """

    def __init__(self, mesh_node, messenger):
        """
        Args:
            mesh_node: The MeshNode instance
            messenger: The MeshMessenger instance (used to send chunks)
        """
        self.node = mesh_node
        self.messenger = messenger

        # Tracks incoming transfers
        # Format: { transfer_id: { "header": {...}, "chunks": {}, "received": 0 } }
        self.incoming_transfers = {}

        # Make sure the received files directory exists
        os.makedirs(RECEIVED_FILES_DIR, exist_ok=True)

    async def send_file(self, file_path: str, recipient_id: str = "broadcast"):
        """
        Send a file to one or all peers in the mesh network.

        Steps:
            1. Validate the file exists
            2. Compute checksum
            3. Split into chunks
            4. Send header (metadata)
            5. Send each chunk with a small delay between them

        Args:
            file_path: Full path to the file on disk
            recipient_id: Target node ID or 'broadcast'
        """
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        print(f"\nPreparing to send: {file_name} ({file_size} bytes)")

        # Step 1: Compute checksum before sending
        checksum = compute_checksum(file_path)
        logger.info(f"File checksum: {checksum}")

        # Step 2: Split into chunks
        chunks = split_file_into_chunks(file_path)
        total_chunks = len(chunks)

        print(f"Split into {total_chunks} chunk(s) of up to {CHUNK_SIZE // 1024}KB each")

        # Step 3: Create a unique ID for this transfer session
        transfer_id = str(uuid.uuid4())

        # Step 4: Send the header first
        # The header tells the receiver what to expect before any chunks arrive
        header_message = {
            "message_id": str(uuid.uuid4()),
            "sender_id": self.node.node_id,
            "sender_name": self.node.node_name,
            "recipient_id": recipient_id,
            "timestamp": time.time(),
            "hop_count": 0,
            "max_hops": 10,
            "type": "file_header",
            "transfer_id": transfer_id,
            "file_name": file_name,
            "file_size": file_size,
            "total_chunks": total_chunks,
            "checksum": checksum,
        }

        self.node.mark_seen(header_message["message_id"])
        await self.messenger._broadcast_to_peers(header_message)
        logger.info(f"Header sent for transfer {transfer_id[:8]}")

        # Step 5: Send each chunk
        for index, chunk_data in enumerate(chunks):
            chunk_message = {
                "message_id": str(uuid.uuid4()),
                "sender_id": self.node.node_id,
                "sender_name": self.node.node_name,
                "recipient_id": recipient_id,
                "timestamp": time.time(),
                "hop_count": 0,
                "max_hops": 10,
                "type": "file_chunk",
                "transfer_id": transfer_id,
                "chunk_index": index,
                "total_chunks": total_chunks,
                "data": chunk_data,
            }

            self.node.mark_seen(chunk_message["message_id"])
            await self.messenger._broadcast_to_peers(chunk_message)

            # Show progress
            progress = round(((index + 1) / total_chunks) * 100)
            print(f"  Sending... {progress}% ({index + 1}/{total_chunks} chunks)", end="\r")

            # Small delay between chunks to avoid overwhelming peers
            await asyncio.sleep(0.05)

        print(f"\nFile sent successfully: {file_name}")
        logger.info(f"Transfer complete: {transfer_id[:8]}")

    def handle_incoming(self, message: dict):
        """
        Process an incoming file-related message.

        Called by the messenger when a message of type
        'file_header' or 'file_chunk' is received.

        Args:
            message: The raw message dictionary
        """
        msg_type = message.get("type")

        if msg_type == "file_header":
            self._handle_header(message)

        elif msg_type == "file_chunk":
            self._handle_chunk(message)

    def _handle_header(self, message: dict):
        """
        Register a new incoming file transfer when the header arrives.

        The header tells us the filename, size, total chunks, and checksum
        so we can prepare to receive and verify the file.
        """
        transfer_id = message.get("transfer_id")

        if transfer_id in self.incoming_transfers:
            return  # Already registered this transfer

        self.incoming_transfers[transfer_id] = {
            "header": message,
            "chunks": {},       # Will store chunk_index -> data
            "received": 0,      # How many chunks received so far
            "started_at": time.time(),
        }

        print(f"\n[Incoming file] {message.get('file_name')} "
              f"from {message.get('sender_name')} "
              f"({message.get('file_size')} bytes, "
              f"{message.get('total_chunks')} chunks)")

    def _handle_chunk(self, message: dict):
        """
        Store an incoming chunk and check if the transfer is complete.

        Once all chunks are received, reassemble and verify the file.
        """
        transfer_id = message.get("transfer_id")

        # If we receive a chunk before the header, create a placeholder
        if transfer_id not in self.incoming_transfers:
            self.incoming_transfers[transfer_id] = {
                "header": None,
                "chunks": {},
                "received": 0,
                "started_at": time.time(),
            }

        transfer = self.incoming_transfers[transfer_id]
        chunk_index = message.get("chunk_index")
        total_chunks = message.get("total_chunks")

        # Store this chunk if we have not seen it before
        if chunk_index not in transfer["chunks"]:
            transfer["chunks"][chunk_index] = message.get("data")
            transfer["received"] += 1

            progress = round((transfer["received"] / total_chunks) * 100)
            print(f"  Receiving... {progress}% ({transfer['received']}/{total_chunks})", end="\r")

        # Check if all chunks have arrived
        if transfer["received"] >= total_chunks:
            self._reassemble_file(transfer_id)

    def _reassemble_file(self, transfer_id: str):
        """
        Reassemble chunks into the original file and verify its integrity.

        Steps:
            1. Sort chunks by index
            2. Decode each chunk from base64 back to binary
            3. Write all chunks to a new file
            4. Compute checksum of the new file
            5. Compare with the original checksum from the header
        """
        transfer = self.incoming_transfers[transfer_id]
        header = transfer.get("header")

        if not header:
            logger.warning(f"Cannot reassemble {transfer_id[:8]}: header not received")
            return

        file_name = header.get("file_name")
        original_checksum = header.get("checksum")
        total_chunks = header.get("total_chunks")

        output_path = os.path.join(RECEIVED_FILES_DIR, file_name)

        print(f"\nReassembling {file_name}...")

        try:
            with open(output_path, "wb") as f:
                # Write chunks in correct order
                for i in range(total_chunks):
                    chunk_data = transfer["chunks"].get(i)
                    if chunk_data is None:
                        logger.error(f"Missing chunk {i} for transfer {transfer_id[:8]}")
                        return
                    # Decode base64 back to binary and write
                    f.write(base64.b64decode(chunk_data))

            # Verify checksum
            received_checksum = compute_checksum(output_path)

            if received_checksum == original_checksum:
                elapsed = round(time.time() - transfer["started_at"], 2)
                print(f"File received and verified: {output_path}")
                print(f"Transfer completed in {elapsed}s")
            else:
                print(f"Checksum mismatch. File may be corrupted.")
                print(f"  Expected : {original_checksum}")
                print(f"  Got      : {received_checksum}")
                os.remove(output_path)

        except Exception as e:
            logger.error(f"Reassembly failed: {e}")

        # Clean up transfer session from memory
        del self.incoming_transfers[transfer_id]
