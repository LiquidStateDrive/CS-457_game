#!/usr/bin/env python3
"""Nine Men's Morris Game Client CLI.

Conforms to:
- docs/other_specifications.md (-h, -i hostname, -p port, DNS resolution exception handling)
- docs/protocol_blueprint.md
- docs/sequence_diagram.md
"""

import argparse
import select
import socket
import sys
import time
from typing import Optional

from src.cli_renderer import render_board, render_status
from src.game import GameEngine, normalize_player_id
from src.protocol import MessageBuffer, serialize_message


def parse_args(args=None):
    """Parses command line arguments for client.py."""
    parser = argparse.ArgumentParser(
        description="Nine Men's Morris Game Client",
        add_help=True,
    )
    parser.add_argument(
        "-i",
        "--host",
        dest="host",
        type=str,
        required=True,
        help="Server DNS hostname (required)",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        required=True,
        help="Server port (required)",
    )
    return parser.parse_args(args)


def resolve_server(hostname: str, port: int) -> str:
    """Resolves DNS hostname to IP address with explicit exception handling.

    Adheres to docs/other_specifications.md:
    - DNS resolution errors must be caught explicitly.
    - Output clear, user-friendly error advising to check router DNS configuration.
    - Exits cleanly with status code 1.
    """
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror as e:
        sys.stderr.write(
            f"Error: Unable to resolve server hostname '{hostname}'.\n"
            "Please check your network connection and router DNS configuration.\n"
        )
        sys.exit(1)


class GameClient:
    """Manages client socket connection, UI prompts, and message loop."""

    def __init__(self, host: str, port: int, player_name: str = "Player") -> None:
        self.host: str = host
        self.port: int = port
        self.player_name: str = player_name
        self.sock: Optional[socket.socket] = None
        self.buffer: MessageBuffer = MessageBuffer()

        self.assigned_id: str = ""
        self.opponent_name: str = "Opponent"
        self.is_running: bool = False
        self.latest_state: Optional[dict] = None
        self.game_helper: GameEngine = GameEngine()

    def connect(self) -> None:
        """Resolves DNS, opens TCP socket, and sends initial CONNECT message."""
        ip = resolve_server(self.host, self.port)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, self.port))
            print(f"Connected to {self.host} ({ip}):{self.port}")
        except OSError as e:
            sys.stderr.write(f"Connection failed: {e}\n")
            sys.exit(1)

        # Send CONNECT message
        connect_msg = serialize_message(
            "CONNECT",
            "client",
            {"player_name": self.player_name},
        )
        self.sock.sendall(connect_msg)

    def prompt_for_move(self) -> None:
        """Prompts the user for a move based on the current phase."""
        if not self.latest_state:
            return

        unplaced = (
            self.latest_state.get("player_1_unplaced", 0)
            if self.assigned_id == "player_1"
            else self.latest_state.get("player_2_unplaced", 0)
        )
        eliminated = (
            self.latest_state.get("player_1_eliminated", 0)
            if self.assigned_id == "player_1"
            else self.latest_state.get("player_2_eliminated", 0)
        )

        from_point = ""
        to_point = ""
        eliminate_point = ""

        try:
            if unplaced > 0:
                print(f"\n[Placement Phase - {unplaced} pieces remaining to place]")
                to_input = input("Enter board point to place piece (e.g. A1) or 'q' to forfeit: ").strip().upper()
                if to_input in ("Q", "QUIT"):
                    self.send_forfeit()
                    return
                to_point = to_input
            else:
                phase_name = "Flying Phase" if eliminated == 6 else "Movement Phase"
                print(f"\n[{phase_name}]")
                from_input = input("Enter piece point to move FROM (e.g. A1) or 'q' to forfeit: ").strip().upper()
                if from_input in ("Q", "QUIT"):
                    self.send_forfeit()
                    return
                from_point = from_input

                to_input = input("Enter destination point to move TO (e.g. A4): ").strip().upper()
                to_point = to_input

            # Check if this move completes a mill
            self.game_helper.board = dict(self.latest_state.get("board", {}))
            temp_board = dict(self.game_helper.board)
            if from_point:
                temp_board[from_point] = ""
            temp_board[to_point] = "player 1" if self.assigned_id == "player_1" else "player 2"

            if self.game_helper.forms_mill_at(to_point, self.assigned_id, temp_board):
                print("*** MILL FORMED! ***")
                elim_input = input("Enter opponent piece to eliminate (e.g. B4): ").strip().upper()
                eliminate_point = elim_input

            # Send MOVE message
            move_msg = serialize_message(
                "MOVE",
                self.assigned_id,
                {"from": from_point, "to": to_point, "eliminate": eliminate_point},
            )
            self.sock.sendall(move_msg)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting match.")
            self.send_forfeit()

    def send_forfeit(self) -> None:
        """Sends DISCONNECT surrender packet and closes connection."""
        if self.sock:
            try:
                msg = serialize_message(
                    "DISCONNECT",
                    self.assigned_id or "client",
                    {"message": "Player surrendered."},
                )
                self.sock.sendall(msg)
            except OSError:
                pass
        self.is_running = False

    def handle_message(self, msg: dict) -> None:
        """Processes messages received from the game server."""
        msg_type = msg.get("msg_type")
        payload = msg.get("payload", {})

        if msg_type == "CONNECTED":
            self.assigned_id = payload.get("assigned_id", "")
            waiting = payload.get("waiting", 0)
            if waiting == 1:
                print(f"Registered as {self.assigned_id}. Waiting for an opponent to join...")
            else:
                print(f"Registered as {self.assigned_id}. Opponent joined!")

        elif msg_type == "GAME_START":
            self.assigned_id = payload.get("assigned_id", self.assigned_id)
            self.opponent_name = payload.get("opponent_name", "Opponent")
            starting_turn = payload.get("starting_turn", "player_1")
            print(f"\n=== MATCH STARTED ===")
            print(f"You: {self.assigned_id} ({self.player_name}) vs {self.opponent_name}")
            print(f"Starting turn: {starting_turn}\n")

        elif msg_type == "STATE_UPDATE":
            self.latest_state = payload
            board = payload.get("board", {})
            next_turn = payload.get("next_turn", "")
            print("\n" + render_board(board))
            print(render_status(self.assigned_id, self.opponent_name, payload))

            if next_turn == self.assigned_id:
                self.prompt_for_move()

        elif msg_type == "ERROR":
            err_code = payload.get("error", "ERROR")
            err_msg = payload.get("message", "")
            print(f"\n[SERVER ERROR - {err_code}]: {err_msg}")
            if self.latest_state and self.latest_state.get("next_turn") == self.assigned_id:
                # Prompt again on move error
                self.prompt_for_move()

        elif msg_type == "GAME_OVER":
            winner = payload.get("winner", "")
            msg_text = payload.get("message", "")
            print(f"\n=== GAME OVER ===")
            if winner == self.assigned_id:
                print(f"CONGRATULATIONS! You won! ({msg_text})")
            else:
                print(f"Game over. Winner: {winner} ({msg_text})")
            self.is_running = False

    def run(self) -> None:
        """Main client loop reading server packets."""
        self.connect()
        self.is_running = True
        try:
            while self.is_running:
                readable, _, _ = select.select([self.sock], [], [], 0.5)
                if readable:
                    data = self.sock.recv(4096)
                    if not data:
                        print("Disconnected from server.")
                        break
                    messages = self.buffer.append(data)
                    for m in messages:
                        self.handle_message(m)
        except KeyboardInterrupt:
            self.send_forfeit()
        finally:
            if self.sock:
                self.sock.close()


def main():
    args = parse_args()
    client = GameClient(host=args.host, port=args.port)
    client.run()


if __name__ == "__main__":
    main()
