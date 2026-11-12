"""Unit tests for src/protocol.py adhering to docs/protocol_blueprint.md."""

import unittest
from jsonschema import ValidationError
from src.protocol import (
    MessageBuffer,
    create_message,
    serialize_message,
    validate_message,
)


class TestProtocolSchemas(unittest.TestCase):
    """Test schema validation for all message types."""

    def test_valid_connect_message(self):
        msg = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "payload": {"player_name": "Alice"},
        }
        validate_message(msg)

    def test_connect_missing_field(self):
        msg = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "payload": {"player_name": "Alice"},
        }
        with self.assertRaises(ValidationError):
            validate_message(msg)

    def test_connect_extra_field(self):
        msg = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "admin": True,
            "payload": {"player_name": "Alice"},
        }
        with self.assertRaises(ValidationError):
            validate_message(msg)

    def test_valid_connected_message(self):
        msg = {
            "msg_type": "CONNECTED",
            "sender": "server",
            "timestamp": 1728000001.0,
            "payload": {"assigned_id": "player_1", "waiting": 1},
        }
        validate_message(msg)

    def test_valid_game_start_message(self):
        msg = {
            "msg_type": "GAME_START",
            "sender": "server",
            "timestamp": 1728000002.0,
            "payload": {
                "assigned_id": "player_1",
                "opponent_name": "Bob",
                "starting_turn": "player_1",
            },
        }
        validate_message(msg)

    def test_valid_move_message(self):
        msg = {
            "msg_type": "MOVE",
            "sender": "player_1",
            "timestamp": 1728000003.0,
            "payload": {"from": "A4", "to": "A1", "eliminate": "B4"},
        }
        validate_message(msg)

    def test_valid_move_placement_empty_fields(self):
        msg = {
            "msg_type": "MOVE",
            "sender": "player_1",
            "timestamp": 1728000003.0,
            "payload": {"from": "", "to": "A1", "eliminate": ""},
        }
        validate_message(msg)

    def test_valid_state_update_message(self):
        msg = {
            "msg_type": "STATE_UPDATE",
            "sender": "server",
            "timestamp": 1728000004.0,
            "payload": {
                "next_turn": "player_2",
                "player_1_unplaced": 3,
                "player_1_eliminated": 0,
                "player_2_unplaced": 4,
                "player_2_eliminated": 0,
                "board": {"A1": "player 1", "A4": "", "A7": "player 2"},
            },
        }
        validate_message(msg)

    def test_valid_error_message(self):
        msg = {
            "msg_type": "ERROR",
            "sender": "server",
            "timestamp": 1728000005.0,
            "payload": {
                "error": "OUT_OF_TURN",
                "message": "Move attempted out of turn",
            },
        }
        validate_message(msg)

    def test_valid_disconnect_message(self):
        msg = {
            "msg_type": "DISCONNECT",
            "sender": "player_1",
            "timestamp": 1728000006.0,
            "payload": {"message": "Player surrendered."},
        }
        validate_message(msg)

    def test_valid_reconnect_message(self):
        msg = {
            "msg_type": "RECONNECT",
            "sender": "client",
            "timestamp": 1728000008.0,
            "payload": {"player_id": "player_1"},
        }
        validate_message(msg)

    def test_valid_game_over_message(self):
        msg = {
            "msg_type": "GAME_OVER",
            "sender": "server",
            "timestamp": 1728000007.0,
            "payload": {"winner": "player_1", "message": "VICTORY"},
        }
        validate_message(msg)

    def test_unknown_msg_type(self):
        msg = {
            "msg_type": "UNKNOWN_ACTION",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "payload": {},
        }
        with self.assertRaises(ValidationError):
            validate_message(msg)


class TestMessageBufferAndFraming(unittest.TestCase):
    """Test message framing, buffering, fragmentation, and concatenation."""

    def test_serialize_and_buffer_single(self):
        buf = MessageBuffer()
        raw = serialize_message(
            "CONNECT", "player_1", {"player_name": "Eli"}, timestamp=1728000000.0
        )
        self.assertTrue(raw.endswith(b"\n"))
        msgs = buf.append(raw)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["msg_type"], "CONNECT")
        self.assertEqual(msgs[0]["payload"]["player_name"], "Eli")

    def test_fragmented_delivery(self):
        buf = MessageBuffer()
        raw = serialize_message(
            "DISCONNECT", "player_2", {"message": "Surrender"}, timestamp=1728000000.0
        )
        part1 = raw[:10]
        part2 = raw[10:]

        msgs1 = buf.append(part1)
        self.assertEqual(msgs1, [])

        msgs2 = buf.append(part2)
        self.assertEqual(len(msgs2), 1)
        self.assertEqual(msgs2[0]["msg_type"], "DISCONNECT")

    def test_concatenated_delivery(self):
        buf = MessageBuffer()
        raw1 = serialize_message(
            "ERROR", "server", {"error": "INVALID_MOVE", "message": "Not legal"}, timestamp=1.0
        )
        raw2 = serialize_message(
            "GAME_OVER", "server", {"winner": "player_2", "message": "VICTORY"}, timestamp=2.0
        )
        msgs = buf.append(raw1 + raw2)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["msg_type"], "ERROR")
        self.assertEqual(msgs[1]["msg_type"], "GAME_OVER")


if __name__ == "__main__":
    unittest.main()
