"""Protocol serialization, deserialization, framing, and schema definitions.

Strictly conforms to docs/protocol_blueprint.md and rules/application_layer_protocol.md.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple
from jsonschema import ValidationError, validate

BASE_ENVELOPE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "msg_type": {"type": "string"},
        "sender": {"type": "string"},
        "timestamp": {"type": "number"},
        "payload": {"type": "object"},
    },
    "required": ["msg_type", "sender", "timestamp", "payload"],
    "additionalProperties": False,
}

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "CONNECT": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "CONNECT"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "player_name": {"type": "string", "minLength": 1},
                },
                "required": ["player_name"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "CONNECTED": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "CONNECTED"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "assigned_id": {"type": "string"},
                    "waiting": {"type": "integer"},
                },
                "required": ["assigned_id", "waiting"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "GAME_START": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "GAME_START"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "assigned_id": {"type": "string"},
                    "opponent_name": {"type": "string"},
                    "starting_turn": {"type": "string"},
                },
                "required": ["assigned_id", "opponent_name", "starting_turn"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "MOVE": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "MOVE"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "eliminate": {"type": "string"},
                },
                "required": ["from", "to", "eliminate"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "STATE_UPDATE": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "STATE_UPDATE"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "next_turn": {"type": "string"},
                    "player_1_unplaced": {"type": "integer", "minimum": 0},
                    "player_1_eliminated": {"type": "integer", "minimum": 0},
                    "player_2_unplaced": {"type": "integer", "minimum": 0},
                    "player_2_eliminated": {"type": "integer", "minimum": 0},
                    "board": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": [
                    "next_turn",
                    "player_1_unplaced",
                    "player_1_eliminated",
                    "player_2_unplaced",
                    "player_2_eliminated",
                    "board",
                ],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "ERROR": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "ERROR"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["error", "message"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "DISCONNECT": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "DISCONNECT"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "RECONNECT": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "RECONNECT"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "player_id": {"type": "string"},
                },
                "required": ["player_id"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
    "GAME_OVER": {
        "type": "object",
        "properties": {
            "msg_type": {"type": "string", "const": "GAME_OVER"},
            "sender": {"type": "string"},
            "timestamp": {"type": "number"},
            "payload": {
                "type": "object",
                "properties": {
                    "winner": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["winner", "message"],
                "additionalProperties": False,
            },
        },
        "required": ["msg_type", "sender", "timestamp", "payload"],
        "additionalProperties": False,
    },
}


def validate_message(message: Dict[str, Any]) -> None:
    """Validates a message dictionary against the protocol specification."""
    validate(instance=message, schema=BASE_ENVELOPE_SCHEMA)
    msg_type = message.get("msg_type")
    if msg_type not in SCHEMAS:
        raise ValidationError(f"Unknown msg_type: {msg_type}")
    validate(instance=message, schema=SCHEMAS[msg_type])


def create_message(
    msg_type: str,
    sender: str,
    payload: Dict[str, Any],
    timestamp: Optional[float] = None,
) -> Dict[str, Any]:
    """Creates a protocol message dictionary conforming to the blueprint."""
    if timestamp is None:
        timestamp = time.time()
    msg = {
        "msg_type": msg_type,
        "sender": sender,
        "timestamp": float(timestamp),
        "payload": payload,
    }
    validate_message(msg)
    return msg


def serialize_message(
    msg_type: str,
    sender: str,
    payload: Dict[str, Any],
    timestamp: Optional[float] = None,
) -> bytes:
    """Serializes a message to newline-delimited UTF-8 JSON bytes."""
    msg = create_message(msg_type, sender, payload, timestamp=timestamp)
    return (json.dumps(msg) + "\n").encode("utf-8")


class MessageBuffer:
    """Buffers stream data and yields complete newline-delimited JSON messages."""

    def __init__(self) -> None:
        self._buffer: str = ""

    def append(self, data: bytes) -> List[Dict[str, Any]]:
        """Appends incoming bytes to buffer and extracts complete valid JSON messages."""
        self._buffer += data.decode("utf-8")
        messages: List[Dict[str, Any]] = []

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            validate_message(parsed)
            messages.append(parsed)

        return messages

    def clear(self) -> None:
        """Clears the buffer."""
        self._buffer = ""
