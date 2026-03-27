"""
mesh/api.py

FastAPI server that exposes the mesh node functionality
as HTTP endpoints for the Flutter mobile app to consume.

Endpoints:
    GET  /status          - returns node info and peer list
    GET  /messages        - returns all received messages
    POST /send/message    - sends a text message to all peers
    POST /send/file       - sends a file to all peers
    GET  /peers           - returns list of known peers

The Flutter app calls these endpoints over localhost.
On a real device, this server runs as a background service.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from loguru import logger


# Request body models
# Pydantic models define what JSON the Flutter app must send

class TextMessageRequest(BaseModel):
    content: str
    recipient_id: str = "broadcast"

class FileMessageRequest(BaseModel):
    file_path: str
    recipient_id: str = "broadcast"


def create_api(node, messenger, file_transfer):
    """
    Create and configure the FastAPI application.

    We pass in the node, messenger, and file_transfer instances
    so the API endpoints can call their methods directly.

    Args:
        node: MeshNode instance
        messenger: MeshMessenger instance
        file_transfer: FileTransfer instance

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="MeshNet Node API",
        description="Local API for the MeshNet Flutter app",
        version="1.0.0"
    )

    # Allow Flutter app to call this API from any origin
    # This is required because Flutter web and mobile make
    # cross-origin requests to the local Python server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/status")
    async def get_status():
        """
        Returns the current node status including peer list.
        Flutter calls this on startup and periodically to refresh the UI.
        """
        return {
            "node": node.get_node_info(),
            "peers": list(node.peers.values()),
            "peer_count": len(node.peers),
        }

    @app.get("/peers")
    async def get_peers():
        """Returns the list of currently known peers."""
        return {
            "peers": list(node.peers.values()),
            "count": len(node.peers)
        }

    @app.get("/messages")
    async def get_messages():
        """
        Returns all messages received by this node.
        Flutter polls this endpoint to display the chat timeline.
        """
        return {
            "messages": messenger.received_messages,
            "count": len(messenger.received_messages)
        }

    @app.post("/send/message")
    async def send_message(request: TextMessageRequest):
        """
        Send a text message from this node to the mesh network.
        Flutter calls this when the user presses the send button.
        """
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

        message = await messenger.send_message(
            request.content,
            recipient_id=request.recipient_id
        )
        return {"success": True, "message_id": message["message_id"]}

    @app.post("/send/file")
    async def send_file(request: FileMessageRequest):
        """
        Send a file from this node to the mesh network.
        Flutter calls this when the user selects a file to share.
        """
        await file_transfer.send_file(
            request.file_path,
            recipient_id=request.recipient_id
        )
        return {"success": True}

    return app


async def start_api_server(node, messenger, file_transfer, api_port: int = 8000):
    """
    Start the FastAPI server as an async task so it runs
    alongside the mesh node without blocking it.

    Args:
        node: MeshNode instance
        messenger: MeshMessenger instance
        file_transfer: FileTransfer instance
        api_port: Port for the HTTP API (default 8000)
    """
    app = create_api(node, messenger, file_transfer)

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=api_port,
        log_level="warning"  # Keep logs clean
    )
    server = uvicorn.Server(config)
    logger.info(f"API server starting on port {api_port}")
    await server.serve()
