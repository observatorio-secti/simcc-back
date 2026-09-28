import asyncio
import json
import secrets
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from simcc.core.logging.handlers import LOG_DESTINATIONS
from simcc.core.settings import Settings

router = APIRouter(tags=['Logs'])
settings = Settings()

# Secure fallback token generated on startup if none is configured
FALLBACK_TOKEN = secrets.token_hex(24)

# Keep track of active subscriber queues and their event loop
active_queues: Set[tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = set()

# Limit the maximum concurrent WebSocket connections to prevent resource exhaustion (DoS protection)
MAX_CONCURRENT_CONNECTIONS = 5


def broadcast_log_to_websockets(log_data: dict) -> None:
    """Synchronous log destination callback registered with LOG_DESTINATIONS."""
    if not active_queues:
        return

    log_str = json.dumps(log_data, default=str)
    for q, loop in list(active_queues):
        try:
            loop.call_soon_threadsafe(q.put_nowait, log_str)
        except Exception:
            pass


# Dynamically register the destination safely
if broadcast_log_to_websockets not in LOG_DESTINATIONS:
    LOG_DESTINATIONS.append(broadcast_log_to_websockets)


@router.websocket('/logs/stream')
async def stream_logs(websocket: WebSocket):
    # Check concurrent connections limit (Rate limiting/DoS protection)
    if len(active_queues) >= MAX_CONCURRENT_CONNECTIONS:
        await websocket.close(
            code=4008
        )  # Policy Violation / Too many connections
        return

    token = websocket.query_params.get('token')
    expected_token = (
        getattr(settings, 'LOG_WEBSOCKET_TOKEN', None) or FALLBACK_TOKEN
    )
    if not token or token != expected_token:
        await websocket.close(code=4003)
        return

    await websocket.accept()

    q = asyncio.Queue()
    loop = asyncio.get_running_loop()
    conn_info = (q, loop)
    active_queues.add(conn_info)

    try:
        # Keep sending logs to the client
        while True:
            log_str = await q.get()
            await websocket.send_text(log_str)
    except WebSocketDisconnect:
        pass
    finally:
        active_queues.discard(conn_info)
