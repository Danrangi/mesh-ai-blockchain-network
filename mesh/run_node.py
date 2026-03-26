"""
mesh/run_node.py
================
Entry point for running a mesh node.

Run this file on any device to join the mesh network:
    python mesh/run_node.py --name "my-node" --port 8765

The node will:
1. Start up and display its information
2. Begin broadcasting its presence
3. Discover other nodes on the same network
4. Display the network as it forms
"""

import asyncio
import argparse    # For reading command-line arguments
import time
from loguru import logger

from node import MeshNode
from discovery import NodeDiscovery


async def main(node_name: str, port: int):
    """Main function that starts the mesh node."""
    
    print("\n" + "="*50)
    print("  DECENTRALIZED MESH NETWORK - NODE STARTUP")
    print("="*50 + "\n")
    
    # Create the node
    node = MeshNode(node_name=node_name, port=port)
    
    # Create the discovery module and link it to our node
    discovery = NodeDiscovery(node)
    
    print(f"  Node Name : {node.node_name}")
    print(f"  Node ID   : {node.node_id}")
    print(f"  Address   : {node.host}:{node.port}")
    print(f"\n  Starting discovery...\n")
    
    # Start a background task to print network status every 10 seconds
    async def print_status():
        while True:
            await asyncio.sleep(10)
            print(f"\n📊 Network Status — {node.node_name}")
            print(f"   Known peers: {len(node.peers)}")
            for pid, pinfo in node.peers.items():
                print(f"   └─ {pinfo['node_name']} @ {pinfo['host']}:{pinfo['port']}")
            print()
    
    # Run discovery and status printer together
    await asyncio.gather(
        discovery.start(),
        print_status()
    )


if __name__ == "__main__":
    # Set up command line argument parsing
    # This lets you run: python run_node.py --name alice --port 8765
    parser = argparse.ArgumentParser(description="Start a Mesh Network Node")
    parser.add_argument("--name", type=str, default=None, help="Node name")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    args = parser.parse_args()
    
    # Run the async main function
    asyncio.run(main(args.name, args.port))