# CS 457 Project Statement of Work (SOW) & Protocol Specification Template

**Student Name:** Eli Povolny 
**Date:** 2026/9/16
**Course:** CS 457 - Computer Networks  
**Target Server Domain:** `server.povolny.edu`  

---

## 1. Game Selection & Scope (Sprint 0)

> Planning is going to be an iterative process through the sprints so you don't have to have all the details now. Focus on big overview concepts. You will be updating the SOW as we plan.
> You have a lot of freedom to choose a game. There are a couple caveats.  

> - It must run in the console. The lab nodes won't be able to handle extensive graphics.
> - It has to be self-contained. You can use a internet-connector to download you code, but because the architecture must run 5 nodes you won't be able to run 
> - You are encouraged to use python, but I'm not going to make it a strict requirement. The instructor and TA's ability to help with C or Rust, etc will be diminished in other languages.

### 1.1 Game Overview
- **Chosen Game:** Nine Men's Morris
- **Player Capacity:** 2 Players (Simulated via 2 CML Client nodes)
- **Game Summary:** The game is played on a board with 24 points, laid out as follows: 
```
  1   2   3  4  5   6   7
A X——————————X——————————X
  |          |          |
B |   X——————X——————X   |
  |   |      |      |   |
C |   |   X——X——X   |   |
  |   |   |     |   |   |
D X———X———X     X———X———X
  |   |   |     |   |   |
E |   |   X——X——X   |   |
  |   |      |      |   |
F |   X——————X——————X   |
  |   |      |      |   |
G X——————————X——————————X
```
Players each have nine pieces, called "Men". They try to place three men in a line, called a "mill", which allows them to remove an opponents man from the board. (A man gets removed when a player forms a mill. Players can repeatedly break and re-form mills to remove more of their opponents men.)

The game is played in three phases:
- Placement phase: Players place their men on any available point on the board.
- Movement phase: Players move their men to adjacent, open points. 
- Flying phase: When a player has only 3 men remaining, they may move them to *any* available point on the board. 

A player when they reduce their opponent to two men, or when they have no legal moves. In either case, the opponent cannot form any new mills. 

### 1.2 Core Game Rules & Win/Draw Conditions
- **Turn Mechanics:** Players alternate turns, in which they can place/move one piece.
- **Victory Condition:** A player wins when they reduce the other player to only two men, or has no legal moves
- **Draw/Tie Condition:** The game cannot tie. It continues until one player wins. 

---

## 2. Application-Layer Messaging Protocol Blueprint (Sprint 1 Deliverable)

### 2.1 Message Transport & Serialization Format
- **Transport Protocol:** TCP
- **Serialization Format:** JSON
- **Framing Mechanism:** Newline-delimited (`\n`) JSON payloads

### 2.2 Message Schema Definitions

#### Message Types:
1. `CONNECT` (Client -> Server): Request to join the game room.
2. `CONNECTED` (Server -> Client): Player ID assignment and notification of waiting for player status.
3. `GAME_START` (Server -> Clients): Game initiated, assigns roles (e.g. Player X vs Player O).
4. `MOVE` (Client -> Server): Player action (e.g., cell coordinates or answer choice).
5. `STATE_UPDATE` (Server -> Clients): Broadcast current game board / state and active player turn.
6. `DISCONNECT` (Client -> Server): Notification that player wishes to forfeit.
7. `RECONNECT` (Client -> Server): Attemp to reconnect after connection loss. 
8. `GAME_OVER` (Server -> Clients): Victory / Draw notification with final scores.
9. `ERROR` (Server -> Client): Invalid move or malformed packet error.

#### Example JSON Protocol Schema:
```json
{
  "msg_type": "MOVE",
  "player_id": "Player_1",
  "timestamp": 1727000000,
  "payload": {
    "from": "A2",
    "to": "A1",
    "eliminate": "B3"
  }
}
```

#### All other message Schemas defined in `protocol_blueprint.md`

---

### 2.3 Game State Machine (FSM) Design (Sprint 1 Deliverable)
- **State Transitions:** Detail state flow: `INIT` -> `WAITING_FOR_PLAYERS` -> `PLAYER_TURN` -> `EVALUATE_MOVE` -> `GAME_OVER` -> `CLEANUP`.

---

## 3. Game Behavior & Server Concurrency Architecture (Sprint 2 Deliverable)

### 3.1 Server Concurrency Strategy
- **Architecture Choice:** [Multi-Threading (`threading.Thread`) OR Non-blocking I/O multiplexing (`select.select` / `selectors`)]
- **Synchronization Logic:** Explain how shared game state and client list are thread-safe (e.g. `threading.Lock`) to prevent race conditions during turn processing.

### 3.2 State & Score Synchronization Across Clients
- **Turn Enforcement:** Detail how the server validates active player ID before processing moves and broadcasts updated turn notifications to all clients.
- **Score & Board Synchronization:** Describe how state broadcasts keep client screens synchronized in real time.

---

## 4. Coding & AI Implementation Plan (Sprint 3)

- **Permitted AI Tools:** [e.g., GitHub Copilot, ChatGPT, Claude]
- **AI Prompting & Constraint Strategy:** Explain how you will constrain AI models to generate code (in Python or your chosen language) that adheres strictly to the protocol blueprint and FSM designed in Sprints 1 & 2.
- **Implementation Risk Management:** Detail your plan to leverage past programming experience and manage time to ensure code completion on schedule.

---

## 5. CML Multi-Subnet Topology & Wireshark Deployment Plan (Sprint 4 & 5 Deliverable)

> For now you can use the topology below. We may update this when we get to defining subnets.

### 5.1 Subnet & Router Design
- **Subnet A (Client 1):** `192.168.10.0/24` (Interface `Gi0/1` on Router R1)
- **Subnet B (Client 2):** `192.168.11.0/24` (Interface `Gi0/2` on Router R1)
- **Subnet C (Game Server):** `192.168.20.0/24` (Interface `Gi0/1` on Router R2)
- **Router Backbone:** `10.0.0.0/30` (Interface `Gi0/0` on R1 <-> `Gi0/0` on R2)

### 5.2 DHCP Pools & DNS Configuration Plan
- **Router R1 DHCP Pool 1 (`CLIENT1_POOL`):** Leases `192.168.10.10` - `192.168.10.50`, gateway `192.168.10.1`, DNS `10.0.0.2`.
- **Router R1 DHCP Pool 2 (`CLIENT2_POOL`):** Leases `192.168.11.10` - `192.168.11.50`, gateway `192.168.11.1`, DNS `10.0.0.2`.
- **Router R2 Authoritative DNS:** Configured with `ip dns server` and static host mapping `server.[yourlastname].edu` -> `192.168.20.100`.

### 5.3 Deployment Strategy & Wireshark Trace Capture
- **CML Deployment Strategy:** Deploy `server.py` onto Subnet C node (`192.168.20.100`) behind Router R2, and `client.py` onto Subnet A and Subnet B nodes behind Router R1.
- **Cisco Infrastructure Configuration:** Router R1 DHCP pools (`CLIENT1_POOL`, `CLIENT2_POOL`) and Router R2 authoritative DNS (`ip host server.[lastname].edu 192.168.20.100`).
- **Wireshark Trace Capture Plan:** Capture DHCP DORA exchange (`dhcp_negotiation.pcap`) and DNS query/response resolution (`dns_lookup.pcap`).
