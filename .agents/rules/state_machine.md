---
trigger: model_decision
description: "Enforces server state architecture follows specification in fsm_specification.md and sequence_diagram.md"
---

# Networking Protocol Conformance Rules

You are editing or implementing a client and server for a turn based game. The server state must follow the flow logic defined in `fsm_specification.md`. The game state update process must follow the design in `sequence_digaram.md`.

## 1. Single Source of Truth
- **Consult `fsm_specification.md` and `sequence_digaram.md` first:** Before generating, modifying, or server control flow, consult the specification files.
- **User permission for modification** Consult the user before modifying either `fsm_specification.md` or `sequence_digaram.md`, or before straying from the specification. 
