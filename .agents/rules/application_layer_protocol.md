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
