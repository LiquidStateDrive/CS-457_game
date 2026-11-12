"""Nine Men's Morris Game Logic Engine.

Implements rules, phases (placement, movement, flying), mill formation,
and victory conditions as defined in docs/StatementOfWork.md and docs/sequence_diagram.md.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from src.board import ADJACENCY, MILLS, POINTS, are_adjacent, is_valid_point

PLAYER_1 = "player_1"
PLAYER_2 = "player_2"

BOARD_VAL_PLAYER_1 = "player 1"
BOARD_VAL_PLAYER_2 = "player 2"
BOARD_VAL_EMPTY = ""


def normalize_player_id(player: str) -> str:
    """Normalizes player representations to player_1 or player_2."""
    if player in ("player_1", "player 1", "Player 1", "Player_1"):
        return PLAYER_1
    if player in ("player_2", "player 2", "Player 2", "Player_2"):
        return PLAYER_2
    return player


def player_id_to_board_val(player: str) -> str:
    """Returns the board cell string ('player 1' or 'player 2') for a player."""
    norm = normalize_player_id(player)
    if norm == PLAYER_1:
        return BOARD_VAL_PLAYER_1
    if norm == PLAYER_2:
        return BOARD_VAL_PLAYER_2
    return BOARD_VAL_EMPTY


def opponent_of(player: str) -> str:
    """Returns the opponent identifier."""
    return PLAYER_2 if normalize_player_id(player) == PLAYER_1 else PLAYER_1


class GameEngine:
    """Nine Men's Morris Game Rule and State Engine."""

    def __init__(self) -> None:
        self.board: Dict[str, str] = {p: BOARD_VAL_EMPTY for p in POINTS}
        self.player_1_unplaced: int = 9
        self.player_1_eliminated: int = 0
        self.player_2_unplaced: int = 9
        self.player_2_eliminated: int = 0
        self.active_turn: str = PLAYER_1
        self.winner: Optional[str] = None
        self.game_over: bool = False

    def get_unplaced(self, player: str) -> int:
        norm = normalize_player_id(player)
        return self.player_1_unplaced if norm == PLAYER_1 else self.player_2_unplaced

    def get_eliminated(self, player: str) -> int:
        norm = normalize_player_id(player)
        return self.player_1_eliminated if norm == PLAYER_1 else self.player_2_eliminated

    def get_pieces_on_board(self, player: str) -> int:
        target_val = player_id_to_board_val(player)
        return sum(1 for val in self.board.values() if val == target_val)

    def get_total_pieces_remaining(self, player: str) -> int:
        return self.get_unplaced(player) + self.get_pieces_on_board(player)

    def is_flying_phase(self, player: str) -> bool:
        """A player enters the flying phase when all pieces are placed and exactly 3 pieces remain."""
        return self.get_unplaced(player) == 0 and self.get_total_pieces_remaining(player) == 3

    def is_in_mill(self, point: str, player: str, board_state: Optional[Dict[str, str]] = None) -> bool:
        """Determines if a piece at the given point is part of a formed mill."""
        b = board_state or self.board
        target_val = player_id_to_board_val(player)
        if b.get(point) != target_val:
            return False

        for p1, p2, p3 in MILLS:
            if point in (p1, p2, p3):
                if b.get(p1) == target_val and b.get(p2) == target_val and b.get(p3) == target_val:
                    return True
        return False

    def forms_mill_at(self, point: str, player: str, hypothetical_board: Dict[str, str]) -> bool:
        """Checks if a piece placed/moved at point completes any mill in hypothetical_board."""
        target_val = player_id_to_board_val(player)
        if hypothetical_board.get(point) != target_val:
            return False

        for p1, p2, p3 in MILLS:
            if point in (p1, p2, p3):
                if (
                    hypothetical_board.get(p1) == target_val
                    and hypothetical_board.get(p2) == target_val
                    and hypothetical_board.get(p3) == target_val
                ):
                    return True
        return False

    def all_pieces_in_mills(self, player: str, board_state: Optional[Dict[str, str]] = None) -> bool:
        """Checks if all pieces belonging to a player on the board are currently part of a mill."""
        b = board_state or self.board
        target_val = player_id_to_board_val(player)
        player_points = [p for p, val in b.items() if val == target_val]
        if not player_points:
            return False
        return all(self.is_in_mill(p, player, b) for p in player_points)

    def validate_move(
        self, player: str, move_from: str, move_to: str, eliminate: str
    ) -> Tuple[bool, str, str]:
        """Validates a move without modifying state.

        Returns: (is_valid, error_code, error_message)
        """
        norm_player = normalize_player_id(player)
        if self.game_over:
            return False, "GAME_OVER", "The game has already ended."

        if norm_player != self.active_turn:
            return False, "OUT_OF_TURN", "Move attempted out of turn"

        if not is_valid_point(move_to):
            return False, "INVALID_MOVE", f"Destination point '{move_to}' is not a valid board coordinate."

        if self.board[move_to] != BOARD_VAL_EMPTY:
            return False, "INVALID_MOVE", f"Destination point '{move_to}' is already occupied."

        unplaced = self.get_unplaced(norm_player)
        player_val = player_id_to_board_val(norm_player)
        opponent = opponent_of(norm_player)
        opp_val = player_id_to_board_val(opponent)

        # Placement Phase
        if unplaced > 0:
            if move_from != "":
                return (
                    False,
                    "INVALID_MOVE",
                    "During placement phase, 'from' field must be empty.",
                )
        else:
            # Movement or Flying Phase
            if not is_valid_point(move_from):
                return False, "INVALID_MOVE", f"Origin point '{move_from}' is not valid."
            if self.board[move_from] != player_val:
                return (
                    False,
                    "INVALID_MOVE",
                    f"Player does not have a piece at '{move_from}'.",
                )

            # Check adjacency if not flying
            if not self.is_flying_phase(norm_player):
                if not are_adjacent(move_from, move_to):
                    return (
                        False,
                        "INVALID_MOVE",
                        f"Points '{move_from}' and '{move_to}' are not adjacent.",
                    )

        # Check Mill Formation on proposed board
        temp_board = dict(self.board)
        if move_from != "":
            temp_board[move_from] = BOARD_VAL_EMPTY
        temp_board[move_to] = player_val

        mill_formed = self.forms_mill_at(move_to, norm_player, temp_board)

        if mill_formed:
            if not eliminate:
                return (
                    False,
                    "INVALID_MOVE",
                    "A mill was formed; an opponent piece must be selected to eliminate.",
                )
            if not is_valid_point(eliminate):
                return (
                    False,
                    "INVALID_MOVE",
                    f"Eliminate point '{eliminate}' is not valid.",
                )
            if temp_board.get(eliminate) != opp_val:
                return (
                    False,
                    "INVALID_MOVE",
                    f"No opponent piece at '{eliminate}' to eliminate.",
                )

            # Mill protection rule: cannot eliminate piece in a mill unless all opponent pieces are in mills
            if self.is_in_mill(eliminate, opponent, temp_board):
                if not self.all_pieces_in_mills(opponent, temp_board):
                    return (
                        False,
                        "INVALID_MOVE",
                        f"Cannot eliminate piece at '{eliminate}' because it is in a mill and other pieces are not.",
                    )
        else:
            if eliminate != "":
                return (
                    False,
                    "INVALID_MOVE",
                    "No mill was formed; 'eliminate' field must be blank.",
                )

        return True, "", ""

    def apply_move(
        self, player: str, move_from: str, move_to: str, eliminate: str
    ) -> Tuple[bool, str, str]:
        """Validates and applies a move, updating game state, piece counts, and turns.

        Returns: (success, error_code, error_message)
        """
        valid, err_code, err_msg = self.validate_move(player, move_from, move_to, eliminate)
        if not valid:
            return False, err_code, err_msg

        norm_player = normalize_player_id(player)
        player_val = player_id_to_board_val(norm_player)
        opponent = opponent_of(norm_player)

        # Update placement count or board movement
        if self.get_unplaced(norm_player) > 0:
            if norm_player == PLAYER_1:
                self.player_1_unplaced -= 1
            else:
                self.player_2_unplaced -= 1
        else:
            self.board[move_from] = BOARD_VAL_EMPTY

        self.board[move_to] = player_val

        # Handle elimination
        if eliminate:
            self.board[eliminate] = BOARD_VAL_EMPTY
            if opponent == PLAYER_1:
                self.player_1_eliminated += 1
            else:
                self.player_2_eliminated += 1

        # Check victory conditions
        opp_unplaced = self.get_unplaced(opponent)
        opp_remaining = self.get_total_pieces_remaining(opponent)

        # 1. Reduced to <= 2 pieces (only applies after placement)
        if opp_unplaced == 0 and opp_remaining <= 2:
            self.game_over = True
            self.winner = norm_player
            return True, "", ""

        # Switch active turn to check if opponent has legal moves
        self.active_turn = opponent

        # 2. Opponent has no legal moves
        if not self.has_legal_moves(opponent):
            self.game_over = True
            self.winner = norm_player

        return True, "", ""

    def has_legal_moves(self, player: str) -> bool:
        """Determines if the given player has at least one legal move."""
        norm_player = normalize_player_id(player)
        unplaced = self.get_unplaced(norm_player)
        empty_points = [p for p, val in self.board.items() if val == BOARD_VAL_EMPTY]

        if unplaced > 0:
            return len(empty_points) > 0

        # Flying phase
        if self.is_flying_phase(norm_player):
            return len(empty_points) > 0

        # Movement phase: any owned piece adjacent to an empty point
        player_val = player_id_to_board_val(norm_player)
        player_points = [p for p, val in self.board.items() if val == player_val]
        for p in player_points:
            for neighbor in ADJACENCY[p]:
                if self.board[neighbor] == BOARD_VAL_EMPTY:
                    return True

        return False

    def forfeit(self, forfeiting_player: str) -> None:
        """Handles forfeiture by a player."""
        norm = normalize_player_id(forfeiting_player)
        self.winner = opponent_of(norm)
        self.game_over = True

    def get_state_payload(self) -> Dict[str, Any]:
        """Generates the dictionary payload for STATE_UPDATE message."""
        return {
            "next_turn": self.active_turn,
            "player_1_unplaced": self.player_1_unplaced,
            "player_1_eliminated": self.player_1_eliminated,
            "player_2_unplaced": self.player_2_unplaced,
            "player_2_eliminated": self.player_2_eliminated,
            "board": dict(self.board),
        }
