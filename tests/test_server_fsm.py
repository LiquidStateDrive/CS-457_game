"""Unit tests for src/server_fsm.py adhering to docs/fsm_specification.md and docs/sequence_diagram.md."""

import socket
import unittest
from unittest.mock import MagicMock
from src.protocol import MessageBuffer
from src.server_fsm import ClientSession, GameServer, ServerState
from src.game import PLAYER_1, PLAYER_2


class MockSocket:
    """Mock socket object to intercept sent bytes without network I/O."""

    def __init__(self):
        self.sent_data = bytearray()
        self.is_closed = False

    def sendall(self, data: bytes):
        if self.is_closed:
            raise OSError("Socket closed")
        self.sent_data.extend(data)

    def close(self):
        self.is_closed = True


class TestServerFSM(unittest.TestCase):
    """Test server state transitions, move processing, and error handling."""

    def setUp(self):
        self.server = GameServer(host="127.0.0.1", port=0)
        self.server.state = ServerState.WAITING_FOR_PLAYERS

        # Create mock client sessions
        self.mock_sock1 = MockSocket()
        self.mock_sock2 = MockSocket()

        self.session1 = ClientSession(self.mock_sock1, PLAYER_1)
        self.session2 = ClientSession(self.mock_sock2, PLAYER_2)

    def test_initial_state(self):
        srv = GameServer()
        self.assertEqual(srv.state, ServerState.INIT)

    def test_connect_player_1_then_player_2(self):
        self.server.client_1 = self.session1
        # Player 1 connects
        self.server.process_message(
            self.session1,
            {
                "msg_type": "CONNECT",
                "sender": "player_1",
                "timestamp": 1.0,
                "payload": {"player_name": "Alice"},
            },
        )
        self.assertEqual(self.server.state, ServerState.WAITING_FOR_PLAYER)

        buf1 = MessageBuffer()
        msgs1 = buf1.append(bytes(self.mock_sock1.sent_data))
        self.assertEqual(len(msgs1), 1)
        self.assertEqual(msgs1[0]["msg_type"], "CONNECTED")
        self.assertEqual(msgs1[0]["payload"]["waiting"], 1)

        # Player 2 connects
        self.server.client_2 = self.session2
        self.server.process_message(
            self.session2,
            {
                "msg_type": "CONNECT",
                "sender": "player_2",
                "timestamp": 2.0,
                "payload": {"player_name": "Bob"},
            },
        )
        self.assertEqual(self.server.state, ServerState.PLAYER_TURN)

        buf2 = MessageBuffer()
        msgs2 = buf2.append(bytes(self.mock_sock2.sent_data))
        # Player 2 receives CONNECTED, GAME_START, and STATE_UPDATE
        msg_types2 = [m["msg_type"] for m in msgs2]
        self.assertIn("CONNECTED", msg_types2)
        self.assertIn("GAME_START", msg_types2)
        self.assertIn("STATE_UPDATE", msg_types2)

    def test_out_of_turn_move_generates_error(self):
        self.server.client_1 = self.session1
        self.server.client_2 = self.session2
        self.server.state = ServerState.PLAYER_TURN
        self.server.game.active_turn = PLAYER_1

        # Player 2 attempts a move when it's Player 1's turn
        self.server.process_message(
            self.session2,
            {
                "msg_type": "MOVE",
                "sender": "player_2",
                "timestamp": 3.0,
                "payload": {"from": "", "to": "A1", "eliminate": ""},
            },
        )
        # Server must still be in PLAYER_TURN, and P2 receives ERROR
        self.assertEqual(self.server.state, ServerState.PLAYER_TURN)
        buf2 = MessageBuffer()
        msgs2 = buf2.append(bytes(self.mock_sock2.sent_data))
        self.assertTrue(any(m["msg_type"] == "ERROR" and m["payload"]["error"] == "OUT_OF_TURN" for m in msgs2))

    def test_valid_move_broadcasts_state_update(self):
        self.server.client_1 = self.session1
        self.server.client_2 = self.session2
        self.server.state = ServerState.PLAYER_TURN
        self.server.game.active_turn = PLAYER_1

        # Clear mock socket data
        self.mock_sock1.sent_data.clear()
        self.mock_sock2.sent_data.clear()

        # Player 1 makes valid placement at A1
        self.server.process_message(
            self.session1,
            {
                "msg_type": "MOVE",
                "sender": "player_1",
                "timestamp": 4.0,
                "payload": {"from": "", "to": "A1", "eliminate": ""},
            },
        )
        self.assertEqual(self.server.state, ServerState.PLAYER_TURN)
        self.assertEqual(self.server.game.active_turn, PLAYER_2)

        # Both clients receive STATE_UPDATE
        buf1 = MessageBuffer()
        msgs1 = buf1.append(bytes(self.mock_sock1.sent_data))
        self.assertTrue(any(m["msg_type"] == "STATE_UPDATE" for m in msgs1))

        buf2 = MessageBuffer()
        msgs2 = buf2.append(bytes(self.mock_sock2.sent_data))
        self.assertTrue(any(m["msg_type"] == "STATE_UPDATE" for m in msgs2))

    def test_player_forfeit_leads_to_game_over(self):
        self.server.client_1 = self.session1
        self.server.client_2 = self.session2
        self.server.state = ServerState.PLAYER_TURN

        self.mock_sock1.sent_data.clear()
        self.mock_sock2.sent_data.clear()

        # Player 1 forfeits
        self.server.process_message(
            self.session1,
            {
                "msg_type": "DISCONNECT",
                "sender": "player_1",
                "timestamp": 5.0,
                "payload": {"message": "Surrendered"},
            },
        )

        # Game resets to WAITING_FOR_PLAYERS after cleanup
        self.assertEqual(self.server.state, ServerState.WAITING_FOR_PLAYERS)

        # Check that GAME_OVER was sent to Player 2
        buf2 = MessageBuffer()
        msgs2 = buf2.append(bytes(self.mock_sock2.sent_data))
        self.assertTrue(any(m["msg_type"] == "GAME_OVER" and m["payload"]["winner"] == PLAYER_2 for m in msgs2))

    def test_reconnect_flow(self):
        self.server.client_1 = self.session1
        self.server.client_2 = self.session2
        self.server.state = ServerState.PLAYER_TURN

        # Simulate client 1 disconnect
        self.server._handle_client_disconnect(self.session1)
        self.assertEqual(self.server.state, ServerState.WAITING_FOR_RECONNECT)
        self.assertEqual(self.server.disconnected_player_id, PLAYER_1)

        # Simulate reconnect
        mock_sock_reconn = MockSocket()
        reconn_session = ClientSession(mock_sock_reconn, PLAYER_1)
        self.server.client_1 = reconn_session
        self.server.process_message(
            reconn_session,
            {
                "msg_type": "RECONNECT",
                "sender": "client",
                "timestamp": 6.0,
                "payload": {"player_id": PLAYER_1},
            },
        )
        self.assertEqual(self.server.state, ServerState.PLAYER_TURN)
        self.assertIsNone(self.server.disconnected_player_id)


if __name__ == "__main__":
    unittest.main()
