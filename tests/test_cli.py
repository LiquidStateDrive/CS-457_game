"""Unit tests for CLI parsing, DNS resolution handling, and ASCII rendering."""

import io
import socket
import sys
import unittest
from unittest.mock import patch

from client import parse_args as parse_client_args, resolve_server
from server import parse_args as parse_server_args
from src.cli_renderer import (
    COLOR_PLAYER_1,
    COLOR_PLAYER_2,
    COLOR_RESET,
    format_cell,
    render_board,
    render_status,
)


class TestCLIArguments(unittest.TestCase):
    """Test CLI argument parsing for client.py and server.py."""

    def test_server_valid_args(self):
        args = parse_server_args(["-p", "9000"])
        self.assertEqual(args.port, 9000)

    def test_server_missing_port(self):
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new=io.StringIO()):
                parse_server_args([])

    def test_client_valid_args(self):
        args = parse_client_args(["-i", "server.povolny.edu", "-p", "8080"])
        self.assertEqual(args.host, "server.povolny.edu")
        self.assertEqual(args.port, 8080)

    def test_client_missing_host(self):
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new=io.StringIO()):
                parse_client_args(["-p", "8080"])

    def test_client_missing_port(self):
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new=io.StringIO()):
                parse_client_args(["-i", "localhost"])


class TestDNSResolutionHandling(unittest.TestCase):
    """Test explicit DNS error catching and exit code 1 per docs/other_specifications.md."""

    def test_dns_success(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            ip = resolve_server("localhost", 8080)
            self.assertEqual(ip, "127.0.0.1")

    def test_dns_failure_catches_gaierror_and_exits_with_code_1(self):
        with patch("socket.gethostbyname", side_effect=socket.gaierror("Name or service not known")):
            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                with self.assertRaises(SystemExit) as cm:
                    resolve_server("invalid.domain.test", 8080)

                # Exit status must be 1
                self.assertEqual(cm.exception.code, 1)

                # Check error message mentions router DNS configuration
                err_text = stderr_capture.getvalue()
                self.assertIn("Unable to resolve server hostname", err_text)
                self.assertIn("router DNS configuration", err_text)


class TestCLIRenderer(unittest.TestCase):
    """Test ASCII terminal board rendering."""

    def test_format_cell_with_color(self):
        board = {"A1": "player 1", "A4": "player 2", "A7": ""}
        self.assertEqual(format_cell(board, "A1"), f"{COLOR_PLAYER_1}(1){COLOR_RESET}")
        self.assertEqual(format_cell(board, "A4"), f"{COLOR_PLAYER_2}(2){COLOR_RESET}")
        self.assertEqual(format_cell(board, "A7"), "(·)")

    def test_format_cell_without_color(self):
        board = {"A1": "player 1", "A4": "player 2", "A7": ""}
        self.assertEqual(format_cell(board, "A1", use_color=False), "(1)")
        self.assertEqual(format_cell(board, "A4", use_color=False), "(2)")
        self.assertEqual(format_cell(board, "A7", use_color=False), "(·)")

    def test_render_board_structure(self):
        board = {"A1": "player 1", "G7": "player 2"}
        rendered = render_board(board)
        self.assertIn(f"{COLOR_PLAYER_1}(1){COLOR_RESET}", rendered)
        self.assertIn(f"{COLOR_PLAYER_2}(2){COLOR_RESET}", rendered)
        self.assertIn(f"A  {COLOR_PLAYER_1}(1){COLOR_RESET}", rendered)
        self.assertIn("G  (·)", rendered)

        rendered_plain = render_board(board, use_color=False)
        self.assertIn("A  (1)", rendered_plain)
        self.assertNotIn("\033[", rendered_plain)

    def test_render_status(self):
        payload = {
            "player_1_unplaced": 5,
            "player_1_eliminated": 1,
            "player_2_unplaced": 6,
            "player_2_eliminated": 0,
            "next_turn": "player_1",
        }
        status = render_status("player_1", "Bob", payload)
        self.assertIn("player_1", status)
        self.assertIn("YOUR TURN", status)
        self.assertIn("Unplaced = 5", status)
        self.assertIn(COLOR_PLAYER_1, status)
        self.assertIn(COLOR_PLAYER_2, status)


if __name__ == "__main__":
    unittest.main()
