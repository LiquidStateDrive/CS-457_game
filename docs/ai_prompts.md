# CS 457 Game  AI Prompting Framework

**Student Name:** Eli Povolny 
**Date:** 2026/10/3
**Course:** CS 457 - Computer Networks  

---

## 1: Rules

I'm going use a rules file which specifies:

```
---
trigger: model_decision
description: "Enforces strict conformance to the JSON game networking specification in protocol_blueprint.md"
---

# Networking Protocol Conformance Rules

You are editing or implementing network messaging code for the game application layer. All serialized messages, parsers, handlers, and packet structures must strictly adhere to the specification defined in `protocol_blueprint.md`.

## 1. Single Source of Truth
- **Consult `protocol_blueprint.md` first:** Before generating, modifying, or refactoring message structs, classes, or serialisation logic, read `protocol_blueprint.md` to verify field names, types, and envelope structures.
- **No Unilateral Schema Changes:** Never add, delete, rename, or re-type payload fields in code without an explicit instruction from the user to also update `protocol_blueprint.md`.

---

## 2. Envelope & Frame Invariants
Unless explicitly overridden in `protocol_blueprint.md`, every JSON message across the wire must conform to the base envelope structure:
```
This should keep the agent focused on implementing my protocol instead of wandering off on its own. 

## 2: 

I plan to use test driven development to make sure the agent's implementation can always be verified. An example of tests for connect messages is at the bottom of the document. 


## 3: Planning 

The agent will always be prompted for a plan before writing any actual code, such as:

```
/plan Explain how you will implement the JSON messaging protocol so that it conforms to the schema in protocol_bluepring.md and satisfies the tests in message_tests.py
```


















### Example Unit Test for CONNECT message

```python
import unittest
from jsonschema import validate, ValidationError

# JSON Schema enforcing the exact structure, data types, and literal values
CONNECT_SCHEMA = {
    "type": "object",
    "properties": {
        "msg_type": {
            "type": "string",
            "const": "CONNECT"  # Must match the literal string "CONNECT"
        },
        "sender": {
            "type": "string",
            "type": "string"    # Must be the ID of a client
        },
        "timestamp": {
            "type": "number"    # Accepts floats or ints (epoch timestamp)
        },
        "payload": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "required": ["player_name"],
            "additionalProperties": False  # Disallows unexpected fields inside payload
        }
    },
    "required": ["msg_type", "sender", "timestamp", "payload"],
    "additionalProperties": False  # Disallows extra fields in the outer envelope
}


class TestConnectMessageSchema(unittest.TestCase):

    def test_valid_connect_message(self):
        """Verifies that a valid CONNECT message passes validation."""
        valid_msg = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "payload": {
                "player_name": "Player Name"
            }
        }
        # If valid, this call succeeds silently without raising an exception
        validate(instance=valid_msg, schema=CONNECT_SCHEMA)

    def test_invalid_msg_type(self):
        """Fails if msg_type is not 'CONNECT'."""
        bad_msg = {
            "msg_type": "DISCONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "payload": {"player_name": "Player Name"}
        }
        with self.assertRaises(ValidationError):
            validate(instance=bad_msg, schema=CONNECT_SCHEMA)

    def test_missing_required_field(self):
        """Fails if a mandatory top-level key like timestamp is missing."""
        missing_ts = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "payload": {"player_name": "Player Name"}
        }
        with self.assertRaises(ValidationError):
            validate(instance=missing_ts, schema=CONNECT_SCHEMA)

    def test_reject_extra_fields(self):
        """Fails if unexpected fields are injected (due to additionalProperties: False)."""
        extra_keys = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "admin": True,
            "payload": {"player_name": "Player Name"}
        }
        with self.assertRaises(ValidationError):
            validate(instance=extra_keys, schema=CONNECT_SCHEMA)

    def test_invalid_payload_field_type(self):
        """Fails if payload attributes do not match expected types."""
        bad_payload = {
            "msg_type": "CONNECT",
            "sender": "player_1",
            "timestamp": 1728000000.0,
            "payload": {"player_name": 12345}  # Integer instead of string
        }
        with self.assertRaises(ValidationError):
            validate(instance=bad_payload, schema=CONNECT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
```






