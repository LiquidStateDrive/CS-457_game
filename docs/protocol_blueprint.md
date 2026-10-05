# CS 457 Project Protocol Blueprint

**Student Name:** Eli Povolny 
**Date:** 2026/10/3
**Course:** CS 457 - Computer Networks  
**Target Server Domain:** `server.povolny.edu`  

---

## 1. Protocol Architecture & Transport Layer

- **Transport Protocol:** TCP
- **Data Serialization:** JSON (UTF-8 encoded)
- **Message Framing Mechanism:** Newline-delimited JSON (`\n` delimiter)

---

## 2. Base Message Envelope

All application messages follow a consistent JSON envelope schema:

```json
{
  "msg_type": "STRING",
  "sender": "STRING",
  "timestamp": 0.0,
  "payload": {}
}
```

### Envelope Fields:
| Field | Type | Description |
| :--- | :--- | :--- |
| `msg_type` | `string` | Identifier for the message type (`CONNECT`, `CONNECTED`, `GAME_START`, `MOVE`, `STATE_UPDATE`, `ERROR`, `DISCONNECT`, `RECONNECT`, `GAME_OVER`). |
| `sender` | `string` | Originator of the message (`"server"`, `"player_1"`, or `"player_2"`). |
| `timestamp` | `number` | Unix epoch timestamp indicating when the message was sent. |
| `payload` | `object` | Type-specific data container for message arguments or state information. |

---

## 3. Message Types & Schemas

### 3.1 Connection & Lobby Phase

#### `CONNECT` (Client &rarr; Server)
Sent by a client attempting to register with the game server.

```json
{
  "msg_type": "CONNECT",
  "sender": "player_1",
  "timestamp": 1728000000.0,
  "payload": {
    "player_name": "Player Name"
  }
}
```

#### `CONNECTED` (Server &rarr; Client)
Sent by the server to Player acknowledging connection and notifying them whether the server is waiting for an opponent.

```json
{
  "msg_type": "CONNECTED",
  "sender": "server",
  "timestamp": 1728000001.0,
  "payload": {
    "assigned_id": "player_1",
    "waiting": 1
  }
}
```

#### `GAME_START` (Server &rarr; Both Clients)
Sent by the server once both players are connected to initiate the match.

```json
{
  "msg_type": "GAME_START",
  "sender": "server",
  "timestamp": 1728000002.0,
  "payload": {
    "assigned_id": "player_1",
    "opponent_name": "Opponent",
    "starting_turn": "player_1"
  }
}
```

---

### 3.2 Gameplay Phase

#### `MOVE` (Client &rarr; Server)
Sent by the active player to propose an action.

> **Note:** During the placement phase the `from` field will be left blank. When no opposing pieces are eliminated the `eliminated` field will be left blank. 

```json
{
  "msg_type": "MOVE",
  "sender": "player_1",
  "timestamp": 1728000003.0,
  "payload": {
    "from": "A4",
    "to": "A1",
    "eliminated": "B4",
  }
}
```

#### `STATE_UPDATE` (Server &rarr; Both Clients)
Broadcast by the server following move evaluation to synchronize game state across both players.
> **Note:** Game phase is inferred by server and players based on the number of unplaced and eliminated pieces. 
```json
{
  "msg_type": "STATE_UPDATE",
  "sender": "server",
  "timestamp": 1728000004.0,
  "payload": {
    "next_turn": "player_2",
    "player_1_unplaced": 3,
    "player_1_eliminated": 0,
    "player_2_unplaced": 4,
    "player_2_eliminated": 0,
    "board": {"A1" :"player 1", "A4":"", "A7":"player 2","B2" :"" ,"B4" :"player 2","B6" :"","C3" :"","C4" :"","C5" :"","D1" :"player 1","D2" :"player 1","D3" :"","D5" :"player 1","D6" :"","D7" :"player 1","E3" :"player 2","E4" :"player 1","E5" :"","F2" :"","F4" :"player 2","F6" :"","G1" :"player 2","G4" : "","G7" :""}
  }
}
```

---

### 3.3 Status & Error Handling

#### `ERROR` (Server &rarr; Client)
Sent to a client when an invalid move, out-of-turn action, or malformed message occurs.

```json
{
  "msg_type": "ERROR",
  "sender": "server",
  "timestamp": 1728000005.0,
  "payload": {
    "error": "OUT_OF_TURN",
    "message": "Move attempted out of turn"
  }
}
```

---

### 3.4 Termination & Session Management

#### `DISCONNECT` (Client &rarr; Server)
Sent by a player wishing to concede the match.

```json
{
  "msg_type": "DISCONNECT",
  "sender": "player_1",
  "timestamp": 1728000006.0,
  "payload": {
    "message": "Player surrendered."
  }
}
```
#### `RECONNECT` (Client &rarr; Server)
Sent by a disconnected player attempting to resume an active session.

```json
{
  "msg_type": "RECONNECT",
  "sender": "client",
  "timestamp": 1728000008.0,
  "payload": {
    "player_id": "player_1",
  }
}
```

#### `GAME_OVER` (Server &rarr; Both Clients)
Broadcast by the server upon game conclusion (victory condition met, forfeit, or disconnection).

```json
{
  "msg_type": "GAME_OVER",
  "sender": "server",
  "timestamp": 1728000007.0,
  "payload": {
    "winner": "player_1",
    "message": "VICTORY"
  }
}
```
