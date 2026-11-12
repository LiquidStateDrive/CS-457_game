"""Unit tests for src/board.py and src/game.py."""

import unittest
from src.board import ADJACENCY, MILLS, POINTS, are_adjacent, is_valid_point
from src.game import (
    BOARD_VAL_EMPTY,
    BOARD_VAL_PLAYER_1,
    BOARD_VAL_PLAYER_2,
    PLAYER_1,
    PLAYER_2,
    GameEngine,
)
from src.protocol import validate_message, create_message


class TestBoardDefinitions(unittest.TestCase):
    """Test 24-point board coordinates, adjacency, and mill structures."""

    def test_total_points(self):
        self.assertEqual(len(POINTS), 24)
        for p in POINTS:
            self.assertTrue(is_valid_point(p))

    def test_total_mills(self):
        self.assertEqual(len(MILLS), 16)
        for p1, p2, p3 in MILLS:
            self.assertTrue(is_valid_point(p1))
            self.assertTrue(is_valid_point(p2))
            self.assertTrue(is_valid_point(p3))

    def test_adjacency_symmetry(self):
        for p1, neighbors in ADJACENCY.items():
            for p2 in neighbors:
                self.assertIn(p1, ADJACENCY[p2], f"Adjacency not symmetric between {p1} and {p2}")
                self.assertTrue(are_adjacent(p1, p2))
                self.assertTrue(are_adjacent(p2, p1))


class TestGameEngine(unittest.TestCase):
    """Test Nine Men's Morris rule enforcement and game flow."""

    def setUp(self):
        self.game = GameEngine()

    def test_initial_state(self):
        self.assertEqual(self.game.player_1_unplaced, 9)
        self.assertEqual(self.game.player_2_unplaced, 9)
        self.assertEqual(self.game.player_1_eliminated, 0)
        self.assertEqual(self.game.player_2_eliminated, 0)
        self.assertEqual(self.game.active_turn, PLAYER_1)
        self.assertFalse(self.game.game_over)
        self.assertIsNone(self.game.winner)

    def test_out_of_turn_move(self):
        ok, code, msg = self.game.apply_move(PLAYER_2, "", "A1", "")
        self.assertFalse(ok)
        self.assertEqual(code, "OUT_OF_TURN")

    def test_placement_valid(self):
        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A1", "")
        self.assertTrue(ok)
        self.assertEqual(self.game.player_1_unplaced, 8)
        self.assertEqual(self.game.board["A1"], BOARD_VAL_PLAYER_1)
        self.assertEqual(self.game.active_turn, PLAYER_2)

    def test_placement_occupied_point(self):
        self.game.apply_move(PLAYER_1, "", "A1", "")
        ok, code, msg = self.game.apply_move(PLAYER_2, "", "A1", "")
        self.assertFalse(ok)
        self.assertEqual(code, "INVALID_MOVE")

    def test_placement_with_from_nonempty(self):
        ok, code, msg = self.game.apply_move(PLAYER_1, "A1", "A4", "")
        self.assertFalse(ok)
        self.assertEqual(code, "INVALID_MOVE")

    def test_mill_formation_and_elimination(self):
        # P1 places A1, P2 places B2
        self.game.apply_move(PLAYER_1, "", "A1", "")
        self.game.apply_move(PLAYER_2, "", "B2", "")
        # P1 places A4, P2 places B4
        self.game.apply_move(PLAYER_1, "", "A4", "")
        self.game.apply_move(PLAYER_2, "", "B4", "")

        # P1 places A7 to form mill (A1-A4-A7), must eliminate B2
        # First test without eliminate -> should fail
        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A7", "")
        self.assertFalse(ok)
        self.assertEqual(code, "INVALID_MOVE")

        # Now test with eliminate="B2"
        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A7", "B2")
        self.assertTrue(ok)
        self.assertEqual(self.game.board["B2"], BOARD_VAL_EMPTY)
        self.assertEqual(self.game.player_2_eliminated, 1)

    def test_mill_protection_rule(self):
        # Set up a situation where P2 has a mill (B2, B4, B6) and another piece at D2
        self.game.board["B2"] = BOARD_VAL_PLAYER_2
        self.game.board["B4"] = BOARD_VAL_PLAYER_2
        self.game.board["B6"] = BOARD_VAL_PLAYER_2
        self.game.board["D2"] = BOARD_VAL_PLAYER_2

        # P1 forms a mill at A1, A4, A7
        self.game.board["A1"] = BOARD_VAL_PLAYER_1
        self.game.board["A4"] = BOARD_VAL_PLAYER_1

        # Trying to eliminate B2 (which is in mill) when D2 is not in mill should fail
        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A7", "B2")
        self.assertFalse(ok)
        self.assertIn("in a mill", msg)

        # Eliminating D2 should succeed
        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A7", "D2")
        self.assertTrue(ok)
        self.assertEqual(self.game.board["D2"], BOARD_VAL_EMPTY)

    def test_mill_protection_when_all_in_mills(self):
        # When all opponent pieces are in mills, any can be removed
        self.game.board["B2"] = BOARD_VAL_PLAYER_2
        self.game.board["B4"] = BOARD_VAL_PLAYER_2
        self.game.board["B6"] = BOARD_VAL_PLAYER_2

        self.game.board["A1"] = BOARD_VAL_PLAYER_1
        self.game.board["A4"] = BOARD_VAL_PLAYER_1

        ok, code, msg = self.game.apply_move(PLAYER_1, "", "A7", "B2")
        self.assertTrue(ok)
        self.assertEqual(self.game.board["B2"], BOARD_VAL_EMPTY)

    def test_movement_phase(self):
        # Setup board for movement phase with enough pieces for both players
        self.game.player_1_unplaced = 0
        self.game.player_2_unplaced = 0
        self.game.board["A1"] = BOARD_VAL_PLAYER_1
        self.game.board["D1"] = BOARD_VAL_PLAYER_1
        self.game.board["G1"] = BOARD_VAL_PLAYER_1
        self.game.board["D2"] = BOARD_VAL_PLAYER_1

        self.game.board["B2"] = BOARD_VAL_PLAYER_2
        self.game.board["B4"] = BOARD_VAL_PLAYER_2
        self.game.board["B6"] = BOARD_VAL_PLAYER_2
        self.game.board["F2"] = BOARD_VAL_PLAYER_2

        # Valid adjacent move A1 -> A4
        ok, code, msg = self.game.apply_move(PLAYER_1, "A1", "A4", "")
        self.assertTrue(ok)
        self.assertEqual(self.game.board["A1"], BOARD_VAL_EMPTY)
        self.assertEqual(self.game.board["A4"], BOARD_VAL_PLAYER_1)

        # Invalid non-adjacent move for P2 from B2 to G7
        ok, code, msg = self.game.apply_move(PLAYER_2, "B2", "G7", "")
        self.assertFalse(ok)
        self.assertEqual(code, "INVALID_MOVE")

    def test_flying_phase(self):
        # P1 has 3 pieces remaining, 0 unplaced, 6 eliminated
        self.game.player_1_unplaced = 0
        self.game.player_1_eliminated = 6
        self.game.board["A1"] = BOARD_VAL_PLAYER_1
        self.game.board["D1"] = BOARD_VAL_PLAYER_1
        self.game.board["G1"] = BOARD_VAL_PLAYER_1

        # Non-adjacent move should succeed during flying phase
        ok, code, msg = self.game.apply_move(PLAYER_1, "A1", "G7", "")
        self.assertTrue(ok)
        self.assertEqual(self.game.board["A1"], BOARD_VAL_EMPTY)
        self.assertEqual(self.game.board["G7"], BOARD_VAL_PLAYER_1)

    def test_win_condition_reduced_to_two_pieces(self):
        self.game.player_1_unplaced = 0
        self.game.player_2_unplaced = 0
        self.game.player_2_eliminated = 6
        # P2 has 3 pieces remaining on board (B2, B4, D2)
        self.game.board["B2"] = BOARD_VAL_PLAYER_2
        self.game.board["B4"] = BOARD_VAL_PLAYER_2
        self.game.board["D2"] = BOARD_VAL_PLAYER_2

        # P1 has mill at A1, A4, and moves A7 forming mill, eliminating B2
        self.game.board["A1"] = BOARD_VAL_PLAYER_1
        self.game.board["A4"] = BOARD_VAL_PLAYER_1
        self.game.board["G1"] = BOARD_VAL_PLAYER_1

        ok, code, msg = self.game.apply_move(PLAYER_1, "G1", "A7", "B2")
        self.assertTrue(ok)
        self.assertEqual(self.game.player_2_eliminated, 7)
        self.assertTrue(self.game.game_over)
        self.assertEqual(self.game.winner, PLAYER_1)

    def test_win_condition_no_legal_moves(self):
        # P2 has no unplaced pieces and is trapped
        self.game.player_1_unplaced = 0
        self.game.player_2_unplaced = 0
        # P2 has piece at A1. Neighbors are A4 and D1.
        self.game.board["A1"] = BOARD_VAL_PLAYER_2
        self.game.board["A4"] = BOARD_VAL_PLAYER_1
        self.game.board["D1"] = BOARD_VAL_PLAYER_1
        # P1 moves from D7 to G7
        self.game.board["D7"] = BOARD_VAL_PLAYER_1
        self.game.board["G7"] = BOARD_VAL_EMPTY

        # If P2 has only A1 on board, remaining=1 (which would already be game over),
        # so give P2 four pieces total but all trapped
        self.game.board["A7"] = BOARD_VAL_PLAYER_2
        self.game.board["G1"] = BOARD_VAL_PLAYER_2
        self.game.board["G7"] = BOARD_VAL_PLAYER_2
        # Trap all of them
        # A7 neighbors: A4 (P1), D7 (P1)
        # G1 neighbors: D1 (P1), G4 (P1)
        # G7 neighbors: G4 (P1), D7 (P1)
        self.game.board["G4"] = BOARD_VAL_PLAYER_1
        self.game.board["D2"] = BOARD_VAL_PLAYER_1
        self.game.board["D3"] = BOARD_VAL_EMPTY

        # P1 moves D2 to D3 (doesn't form mill)
        ok, code, msg = self.game.apply_move(PLAYER_1, "D2", "D3", "")
        self.assertTrue(ok)
        self.assertTrue(self.game.game_over)
        self.assertEqual(self.game.winner, PLAYER_1)

    def test_forfeit(self):
        self.game.forfeit(PLAYER_1)
        self.assertTrue(self.game.game_over)
        self.assertEqual(self.game.winner, PLAYER_2)

    def test_state_payload_matches_protocol_schema(self):
        payload = self.game.get_state_payload()
        msg = create_message("STATE_UPDATE", "server", payload, timestamp=100.0)
        validate_message(msg)


if __name__ == "__main__":
    unittest.main()
