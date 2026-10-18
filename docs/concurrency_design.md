# CS 457 Project Concurrency Design

**Student Name:** Eli Povolny  
**Date:** 2026/10/3  
**Course:** CS 457 - Computer Networks  
**Target Server Domain:** `server.povolny.edu`  

---

## 1. Concurrency Architecture Selection

For the Nine Men's Morris game server, I chose **Non-blocking I/O Multiplexing via Python's `selectors` module (`selectors.DefaultSelector`)** 

### Rationale 
Selectors are simple, lightweight, and robust. They are inherently thread safe due to using a single threaded event loop. Calls will be handled sequentially in the order defined by the State Machine. The only sensitive part of the networking that must be handled is waiting for `\n` to be recieved before processing messages, because `recv()` will be non-blocking. Because the game flow is bottlenecked by waiting for IO and has very low processing demands, a single threaded approach should have no perofrmance downside. 

**Why not Multi-Threading or Multi-Processing?** While thread-per-client allows simple blocking calls (recv()), it introduces concurrency hazards. While this can be handled with propoer use of locks, it introduces unnecessary complexity and makes debugging more difficult. Multi-Processing with IPC could be used to bypass Pythons inherent single threaded nature, but that would be massive overkill for this simple game, and again, introduces unneeded complexity. 


## 2. Connection Lifecycle and Alignment with the Finite State Machine (FSM)

The server's lifecycle is modeled as a deterministic Finite State Machine (FSM):
$$\text{INIT} \longrightarrow \text{WAITING\_FOR\_PLAYERS} \longrightarrow \text{PLAYER\_TURN} \longleftrightarrow \text{EVALUATE\_MOVE} \longrightarrow \text{GAME\_OVER} \longrightarrow \text{CLEANUP}$$

### Event-Driven State Transitions
The `selectors` event loop acts as the natural driver for this state machine:

1. **`INIT` &rarr; `WAITING_FOR_PLAYERS`**:
   * The server binds to its port, sets the listening socket to non-blocking mode (`server_sock.setblocking(False)`), and registers it with `selector.register(server_sock, selectors.EVENT_READ, data=accept_handler)`.
   * When Client 1 connects, `selector.select()` triggers `accept_handler`. The client socket is registered with `selectors.EVENT_READ` and assigned `player_1`. The server remains in `WAITING_FOR_PLAYERS` waiting for Player 2.
2. **`WAITING_FOR_PLAYERS` &rarr; `PLAYER_TURN`**:
   * When Client 2 connects, the server accepts the socket, registers it, transitions to `PLAYER_TURN`, and broadcasts `GAME_START` to both players.
3. **`PLAYER_TURN` &rarr; `EVALUATE_MOVE` &rarr; `PLAYER_TURN`**:
   * The event loop waits on `selector.select()`. When data arrives on either client socket, the read handler executes.
   * Because processing is strictly sequential, the server evaluates whether the message sender matches `active_turn`. If Player 2 sends a `MOVE` while it is Player 1's turn, the server immediately returns an `ERROR` (`OUT_OF_TURN`) without the move ever touching the game board.
   * If valid, the move updates the board, checks for mill formation or victory conditions, and broadcasts `STATE_UPDATE` to both players before handing the turn to the opponent.
4. **Any State &rarr; `GAME_OVER` / `CLEANUP`**:
    * If `EVALUATE_MOVE` detects that one player has won, the `GAME_OVER` notification with the results will be sent to both players, then both conenctions will be cleaned up. 
   * If a client abruptly disconnects (`recv()` returns 0 bytes) the server enters the **`WAITING_FOR_PLAYER`** state and informs the other client that one client lost connection. 
   * If a client sends a `DISCONNECT` message, the selector triggers disconnection cleanup. The socket is unregistered from the selector, closed, and a `GAME_OVER` notification is dispatched to the remaining player.

Because the FSM is fundamentally reactive and event-driven, mapping socket readiness directly to state transitions provides an unambiguous 1:1 match between network events and game rules.

---

## 3. Thread Safety & Synchronization Guarantee

With `selectors`, **the entire server runs in a single execution thread**:
* **No Race Conditions:** Only one callback executes at any given instant. When a `MOVE` packet is parsed and evaluated, no other code can mutate the board state, modify piece counts, or alter turn flags mid-execution.
* **No Locks or Deadlocks:** Because state mutations are serialized naturally by the single-threaded event loop, locks (`threading.Lock`), condition variables, and mutexes are completely unnecessary.
* **Deterministic Execution:** The server processes messages strictly in the order the OS kernel flags them as readable. This makes network behavior predictable, reproducible, and easy to trace in Wireshark.

---

## 4. Implementation Details & Non-blocking I/O Handling

### 4.1 Message Framing & Buffer Management
TCP is a stream-oriented protocol, meaning message boundaries are not preserved by the transport layer. A single `recv()` call may return:
1. A partial JSON message (fragmentation).
2. Multiple JSON messages concatenated together.

To handle this cleanly in non-blocking mode:
* Each registered client socket holds an associated session object containing a receive buffer (`recv_buffer = ""`).
* When `selectors.EVENT_READ` fires:
  1. `data = sock.recv(4096).decode('utf-8')` is appended to the client's buffer.
  2. The buffer is split on the newline delimiter (`\n`).
  3. All complete JSON lines are parsed and passed into the FSM handler.
  4. Any trailing, incomplete fragment remains in the buffer awaiting the next read event.

### 4.2 Handling Client Disconnections
When a client closes their connection or crashes:
* `sock.recv()` returns an empty byte string (`b""`).
* The server detects this EOF condition, unregisters the file descriptor via `selector.unregister(sock)`, closes the socket, and informs the game state machine to transition into forfeit/concession handling.
