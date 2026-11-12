"""Finite State Machine and Non-blocking Network Server for Nine Men's Morris.

Conforms strictly to:
- docs/fsm_specification.md
- docs/concurrency_design.md
- docs/sequence_diagram.md
- docs/protocol_blueprint.md
- .agents/rules/state_machine.md
"""

from enum import Enum
import logging
import selectors
import socket
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from src.game import PLAYER_1, PLAYER_2, GameEngine
from src.protocol import (
    MessageBuffer,
    create_message,
    serialize_message,
    validate_message,
)

logger = logging.getLogger(__name__)


class ServerState(Enum):
    INIT = "INIT"
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    WAITING_FOR_PLAYER = "WAITING_FOR_PLAYER"
    GAME_START = "GAME_START"
    PLAYER_TURN = "PLAYER_TURN"
    EVALUATE_MOVE = "EVALUATE_MOVE"
    WAITING_FOR_RECONNECT = "WAITING_FOR_RECONNECT"
    GAME_OVER = "GAME_OVER"
    CLEANUP = "CLEANUP"


class ClientSession:
    """Encapsulates a connected client socket, buffer, and player assignment."""

    def __init__(self, sock: socket.socket, player_id: str) -> None:
        self.sock: socket.socket = sock
        self.player_id: str = player_id
        self.player_name: str = ""
        self.buffer: MessageBuffer = MessageBuffer()
        self.is_connected: bool = True

    def send_message(self, msg_type: str, payload: Dict[str, Any]) -> None:
        """Serializes and sends a protocol message over the non-blocking socket."""
        if not self.is_connected:
            return
        data = serialize_message(msg_type, "server", payload)
        try:
            self.sock.sendall(data)
        except OSError as e:
            logger.warning(f"Error sending message to {self.player_id}: {e}")
            self.is_connected = False


class GameServer:
    """Nine Men's Morris Server managing non-blocking I/O multiplexing and state transitions."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host: str = host
        self.port: int = port
        self.state: ServerState = ServerState.INIT
        self.selector: selectors.BaseSelector = selectors.DefaultSelector()
        self.server_sock: Optional[socket.socket] = None
        self.game: GameEngine = GameEngine()

        self.client_1: Optional[ClientSession] = None
        self.client_2: Optional[ClientSession] = None
        self.disconnected_player_id: Optional[str] = None
        self.running: bool = False

    def setup_server_socket(self) -> None:
        """Creates, binds, and registers the listening server socket."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.setblocking(False)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.selector.register(
            self.server_sock, selectors.EVENT_READ, data=self._accept_handler
        )
        self.state = ServerState.WAITING_FOR_PLAYERS
        logger.info(f"Server started and listening on {self.host}:{self.port} [{self.state.value}]")

    def _accept_handler(self, server_sock: socket.socket, mask: int) -> None:
        """Accepts an incoming TCP connection and handles lobby assignment."""
        try:
            conn, addr = server_sock.accept()
        except OSError:
            return

        conn.setblocking(False)
        logger.info(f"Accepted connection from {addr}")

        if self.state == ServerState.WAITING_FOR_PLAYERS:
            # First player connecting
            session = ClientSession(conn, PLAYER_1)
            self.client_1 = session
            self.selector.register(
                conn, selectors.EVENT_READ, data=lambda s, m: self._read_handler(session)
            )
            self.state = ServerState.WAITING_FOR_PLAYER
            logger.info(f"Assigned {PLAYER_1} to {addr} [{self.state.value}]")

        elif self.state == ServerState.WAITING_FOR_PLAYER:
            # Second player connecting
            session = ClientSession(conn, PLAYER_2)
            self.client_2 = session
            self.selector.register(
                conn, selectors.EVENT_READ, data=lambda s, m: self._read_handler(session)
            )
            logger.info(f"Assigned {PLAYER_2} to {addr}")
            # If player 1 is ready, transition to GAME_START when both have sent CONNECT or on connect
            # In our protocol, clients send CONNECT after connecting.

        elif self.state == ServerState.WAITING_FOR_RECONNECT:
            # A disconnected player is reconnecting
            target_id = self.disconnected_player_id
            session = ClientSession(conn, target_id if target_id else PLAYER_1)
            if target_id == PLAYER_1:
                self.client_1 = session
            else:
                self.client_2 = session
            self.selector.register(
                conn, selectors.EVENT_READ, data=lambda s, m: self._read_handler(session)
            )
            logger.info(f"Reconnect socket accepted for {target_id}")

        else:
            # Server is busy / match in progress
            logger.warning("Rejected connection: game room full")
            conn.close()

    def _read_handler(self, session: ClientSession) -> None:
        """Reads incoming bytes from client non-blocking socket and dispatches complete messages."""
        try:
            data = session.sock.recv(4096)
        except OSError:
            data = b""

        if not data:
            # Client disconnected / EOF
            self._handle_client_disconnect(session)
            return

        try:
            messages = session.buffer.append(data)
        except Exception as e:
            logger.error(f"Error parsing message from {session.player_id}: {e}")
            session.send_message("ERROR", {"error": "MALFORMED_MESSAGE", "message": str(e)})
            return

        for msg in messages:
            self.process_message(session, msg)

    def process_message(self, session: ClientSession, msg: Dict[str, Any]) -> None:
        """Processes a validated protocol message based on current FSM state."""
        msg_type = msg.get("msg_type")
        payload = msg.get("payload", {})

        if msg_type == "CONNECT":
            self._handle_connect(session, payload)

        elif msg_type == "RECONNECT":
            self._handle_reconnect(session, payload)

        elif msg_type == "MOVE":
            self._handle_move(session, payload)

        elif msg_type == "DISCONNECT":
            self._handle_forfeit(session, payload)

        else:
            session.send_message(
                "ERROR",
                {"error": "INVALID_MESSAGE_TYPE", "message": f"Unexpected message {msg_type}"},
            )

    def _handle_connect(self, session: ClientSession, payload: Dict[str, Any]) -> None:
        session.player_name = payload.get("player_name", "Anonymous")

        if session == self.client_1 and self.client_2 is None:
            # Player 1 connected, waiting for player 2
            session.send_message(
                "CONNECTED",
                {"assigned_id": session.player_id, "waiting": 1},
            )
            self.state = ServerState.WAITING_FOR_PLAYER

        elif self.client_1 is not None and self.client_2 is not None:
            # Both players present
            session.send_message(
                "CONNECTED",
                {"assigned_id": session.player_id, "waiting": 0},
            )
            # Both connected, trigger GAME_START
            self.state = ServerState.GAME_START
            self._start_game()

    def _start_game(self) -> None:
        """Initializes the game and notifies both clients."""
        self.game = GameEngine()
        p1_name = self.client_1.player_name if self.client_1 else "Player 1"
        p2_name = self.client_2.player_name if self.client_2 else "Player 2"

        if self.client_1:
            self.client_1.send_message(
                "GAME_START",
                {
                    "assigned_id": PLAYER_1,
                    "opponent_name": p2_name,
                    "starting_turn": PLAYER_1,
                },
            )
        if self.client_2:
            self.client_2.send_message(
                "GAME_START",
                {
                    "assigned_id": PLAYER_2,
                    "opponent_name": p1_name,
                    "starting_turn": PLAYER_1,
                },
            )

        self.state = ServerState.PLAYER_TURN
        self.broadcast_state()

    def _handle_move(self, session: ClientSession, payload: Dict[str, Any]) -> None:
        """Evaluates and applies move per sequence diagram."""
        if self.state not in (ServerState.PLAYER_TURN, ServerState.EVALUATE_MOVE):
            session.send_message(
                "ERROR",
                {"error": "INVALID_STATE", "message": "Game is not currently active"},
            )
            return

        self.state = ServerState.EVALUATE_MOVE
        from_pt = payload.get("from", "")
        to_pt = payload.get("to", "")
        eliminate = payload.get("eliminate", "")

        ok, err_code, err_msg = self.game.apply_move(
            session.player_id, from_pt, to_pt, eliminate
        )

        if not ok:
            # Invalid or out-of-turn move: return ERROR to client
            session.send_message("ERROR", {"error": err_code, "message": err_msg})
            self.state = ServerState.PLAYER_TURN
            return

        # Valid move: check victory or update state
        if self.game.game_over:
            self.state = ServerState.GAME_OVER
            self._handle_game_over(self.game.winner or session.player_id, "VICTORY")
        else:
            self.state = ServerState.PLAYER_TURN
            self.broadcast_state()

    def _handle_forfeit(self, session: ClientSession, payload: Dict[str, Any]) -> None:
        """Handles explicit player surrender."""
        self.state = ServerState.GAME_OVER
        self.game.forfeit(session.player_id)
        winner = self.game.winner or (PLAYER_2 if session.player_id == PLAYER_1 else PLAYER_1)
        reason = payload.get("message", "Player surrendered.")
        self._handle_game_over(winner, f"Opponent surrendered: {reason}")

    def _handle_client_disconnect(self, session: ClientSession) -> None:
        """Handles unexpected client disconnection / socket close."""
        session.is_connected = False
        try:
            self.selector.unregister(session.sock)
            session.sock.close()
        except Exception:
            pass

        if self.state in (ServerState.WAITING_FOR_PLAYERS, ServerState.WAITING_FOR_PLAYER):
            # Lobby disconnect
            if session == self.client_1:
                self.client_1 = None
                self.state = ServerState.WAITING_FOR_PLAYERS
            elif session == self.client_2:
                self.client_2 = None
                self.state = ServerState.WAITING_FOR_PLAYER

        elif self.state in (ServerState.PLAYER_TURN, ServerState.EVALUATE_MOVE):
            # Mid-game disconnect -> WAITING_FOR_RECONNECT
            self.disconnected_player_id = session.player_id
            self.state = ServerState.WAITING_FOR_RECONNECT
            other_session = self.client_2 if session == self.client_1 else self.client_1
            if other_session and other_session.is_connected:
                other_session.send_message(
                    "ERROR",
                    {
                        "error": "OPPONENT_DISCONNECTED",
                        "message": "Opponent disconnected. Waiting for reconnect.",
                    },
                )
            else:
                # Both disconnected
                self.state = ServerState.GAME_OVER
                self.cleanup()

        elif self.state == ServerState.WAITING_FOR_RECONNECT:
            # Remaining player also disconnected -> Game Over
            self.state = ServerState.GAME_OVER
            self.cleanup()

    def _handle_reconnect(self, session: ClientSession, payload: Dict[str, Any]) -> None:
        player_id = payload.get("player_id")
        if self.state == ServerState.WAITING_FOR_RECONNECT and player_id == self.disconnected_player_id:
            session.player_id = player_id
            self.disconnected_player_id = None
            self.state = ServerState.PLAYER_TURN
            session.send_message(
                "CONNECTED",
                {"assigned_id": player_id, "waiting": 0},
            )
            self.broadcast_state()
        else:
            session.send_message(
                "ERROR",
                {"error": "RECONNECT_FAILED", "message": "Cannot resume active match"},
            )

    def broadcast_state(self) -> None:
        """Broadcasts STATE_UPDATE to both active clients."""
        payload = self.game.get_state_payload()
        if self.client_1 and self.client_1.is_connected:
            self.client_1.send_message("STATE_UPDATE", payload)
        if self.client_2 and self.client_2.is_connected:
            self.client_2.send_message("STATE_UPDATE", payload)

    def _handle_game_over(self, winner: str, message: str) -> None:
        """Broadcasts GAME_OVER to both players and performs cleanup."""
        payload = {"winner": winner, "message": message}
        if self.client_1 and self.client_1.is_connected:
            self.client_1.send_message("GAME_OVER", payload)
        if self.client_2 and self.client_2.is_connected:
            self.client_2.send_message("GAME_OVER", payload)
        self.state = ServerState.CLEANUP
        self.cleanup()

    def cleanup(self) -> None:
        """Closes client connections and resets FSM to WAITING_FOR_PLAYERS."""
        for session in (self.client_1, self.client_2):
            if session and session.sock:
                try:
                    self.selector.unregister(session.sock)
                    session.sock.close()
                except Exception:
                    pass
        self.client_1 = None
        self.client_2 = None
        self.disconnected_player_id = None
        self.game = GameEngine()
        self.state = ServerState.WAITING_FOR_PLAYERS
        logger.info("Cleanup complete. Reset to WAITING_FOR_PLAYERS.")

    def run_tick(self, timeout: float = 0.1) -> None:
        """Performs a single selector polling tick for event-driven processing."""
        events = self.selector.select(timeout=timeout)
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    def serve_forever(self) -> None:
        """Main non-blocking event loop."""
        self.setup_server_socket()
        self.running = True
        logger.info(f"Nine Men's Morris server running on port {self.port}...")
        try:
            while self.running:
                self.run_tick(timeout=0.1)
        except KeyboardInterrupt:
            logger.info("Server shutting down.")
        finally:
            self.close()

    def close(self) -> None:
        """Shuts down server socket and selector."""
        self.running = False
        self.cleanup()
        if self.server_sock:
            try:
                self.selector.unregister(self.server_sock)
                self.server_sock.close()
            except Exception:
                pass
        self.selector.close()
