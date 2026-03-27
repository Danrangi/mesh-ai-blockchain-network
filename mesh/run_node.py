"""
mesh/run_node.py

Entry point for running a mesh node from the terminal.

Usage:
    python run_node.py --port 8765
    python run_node.py --port 8766

Commands once running:
    Type any text     - broadcast a text message to all peers
    peers             - list connected nodes
    send <filepath>   - send a file to all peers
    quit              - exit
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from node import MeshNode
from discovery import NodeDiscovery
from messaging import MeshMessenger
from filetransfer import FileTransfer
from profile import get_or_create_username
from loguru import logger


async def interactive_prompt(messenger, file_transfer, node):
    """Terminal interface supporting text messages and file sending."""
    loop = asyncio.get_event_loop()

    print("\nCommands:")
    print("  <message>         - broadcast text to all peers")
    print("  peers             - list connected nodes")
    print("  send <filepath>   - send a file to all peers")
    print("  quit              - exit\n")

    while True:
        try:
            user_input = await loop.run_in_executor(None, input, "> ")
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Shutting down node.")
                break

            elif user_input.lower() == "peers":
                if not node.peers:
                    print("No peers connected yet.")
                else:
                    print(f"Connected peers ({len(node.peers)}):")
                    for pid, pinfo in node.peers.items():
                        print(f"  {pinfo['node_name']} @ {pinfo['host']}:{pinfo['port']}")

            elif user_input.lower().startswith("send "):
                # Extract file path from command
                file_path = user_input[5:].strip()
                await file_transfer.send_file(file_path, recipient_id="broadcast")

            else:
                await messenger.send_message(user_input, recipient_id="broadcast")

        except (EOFError, KeyboardInterrupt):
            break


async def main(port: int):
    """Start the mesh node with all modules running together."""

    username = get_or_create_username(port)

    print("\n--- Mesh Node Starting ---")

    node = MeshNode(node_name=username, port=port)
    messenger = MeshMessenger(node)
    file_transfer = FileTransfer(node, messenger)

    # Inject file_transfer into messenger so it can route file messages
    messenger.file_transfer = file_transfer

    discovery = NodeDiscovery(node)

    print(f"  Name    : {node.node_name}")
    print(f"  Node ID : {node.node_id[:16]}...")
    print(f"  Address : {node.host}:{node.port}")
    print()

    await messenger.start_server()

    await asyncio.gather(
        discovery.start(),
        interactive_prompt(messenger, file_transfer, node)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a Mesh Network Node")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    asyncio.run(main(args.port))
