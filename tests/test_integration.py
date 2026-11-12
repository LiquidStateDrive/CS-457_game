"""End-to-End integration test for Nine Men's Morris client-server TCP exchange."""

import socket
import threading
import time
import unittest

from src.protocol import MessageBuffer, serialize_message
from src.server_fsm import GameServer, ServerState


class TestNetworkIntegration(unittest.TestCase):
    """Tests live TCP socket interactions between GameServer and two real client sockets."""

    @classmethod
    def setUpClass(cls):
        cls.server = GameServer(host="127.0.0.1", port=0)
        cls.server.setup_server_socket()
        # Retrieve actual bound port
        cls.port = cls.server.server_sock.getsockname()[1]
        cls.server_running = True

        def server_loop():
            while cls.server_running:
                cls.server.run_tick(timeout=0.05)

        cls.thread = threading.Thread(target=server_loop, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server_running = False
        cls.thread.join(timeout=1.0)
        cls.server.close()

    def test_full_match_handshake_and_gameplay(self):
        # 1. Connect Client 1
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.connect(("127.0.0.1", self.port))
        buf1 = MessageBuffer()

        sock1.sendall(
            serialize_message("CONNECT", "client", {"player_name": "Alice"})
        )
        time.sleep(0.1)
        msgs1 = buf1.append(sock1.recv(4096))
        self.assertEqual(len(msgs1), 1)
        self.assertEqual(msgs1[0]["msg_type"], "CONNECTED")
        self.assertEqual(msgs1[0]["payload"]["assigned_id"], "player_1")
        self.assertEqual(msgs1[0]["payload"]["waiting"], 1)

        # 2. Connect Client 2
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.connect(("127.0.0.1", self.port))
        buf2 = MessageBuffer()

        sock2.sendall(
            serialize_message("CONNECT", "client", {"player_name": "Bob"})
        )
        time.sleep(0.1)

        # Client 2 should receive CONNECTED, GAME_START, and STATE_UPDATE
        data2 = sock2.recv(4096)
        msgs2 = buf2.append(data2)
        types2 = [m["msg_type"] for m in msgs2]
        self.assertIn("CONNECTED", types2)
        self.assertIn("GAME_START", types2)
        self.assertIn("STATE_UPDATE", types2)

        # Client 1 should also receive GAME_START and STATE_UPDATE
        data1 = sock1.recv(4096)
        msgs1_more = buf1.append(data1)
        types1 = [m["msg_type"] for m in msgs1_more]
        self.assertIn("GAME_START", types1)
        self.assertIn("STATE_UPDATE", types1)

        # 3. Client 1 makes valid placement at A1
        sock1.sendall(
            serialize_message(
                "MOVE", "player_1", {"from": "", "to": "A1", "eliminate": ""}
            )
        )
        time.sleep(0.1)

        # Both clients receive STATE_UPDATE showing next_turn == player_2
        state_msg1 = buf1.append(sock1.recv(4096))[0]
        self.assertEqual(state_msg1["msg_type"], "STATE_UPDATE")
        self.assertEqual(state_msg1["payload"]["next_turn"], "player_2")
        self.assertEqual(state_msg1["payload"]["board"]["A1"], "player 1")

        state_msg2 = buf2.append(sock2.recv(4096))[0]
        self.assertEqual(state_msg2["msg_type"], "STATE_UPDATE")
        self.assertEqual(state_msg2["payload"]["next_turn"], "player_2")

        # 4. Client 1 sends out of turn move -> receives ERROR
        sock1.sendall(
            serialize_message(
                "MOVE", "player_1", {"from": "", "to": "A4", "eliminate": ""}
            )
        )
        time.sleep(0.1)
        err_msg1 = buf1.append(sock1.recv(4096))[0]
        self.assertEqual(err_msg1["msg_type"], "ERROR")
        self.assertEqual(err_msg1["payload"]["error"], "OUT_OF_TURN")

        # 5. Client 2 forfeits via DISCONNECT
        sock2.sendall(
            serialize_message(
                "DISCONNECT", "player_2", {"message": "Surrendered"}
            )
        )
        time.sleep(0.1)

        # Client 1 receives GAME_OVER with winner == player_1
        game_over_msg1 = buf1.append(sock1.recv(4096))[0]
        self.assertEqual(game_over_msg1["msg_type"], "GAME_OVER")
        self.assertEqual(game_over_msg1["payload"]["winner"], "player_1")

        sock1.close()
        sock2.close()


if __name__ == "__main__":
    unittest.main()
