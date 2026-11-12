"""ASCII CLI Renderer for Nine Men's Morris."""

from typing import Dict
from src.game import BOARD_VAL_PLAYER_1, BOARD_VAL_PLAYER_2

COLOR_PLAYER_1 = "\033[1;36m"  # Bold Cyan
COLOR_PLAYER_2 = "\033[1;31m"  # Bold Red
COLOR_RESET = "\033[0m"


def format_cell(board: Dict[str, str], point: str, use_color: bool = True) -> str:
    """Formats a board cell into a 3-character visual representation (optionally ANSI color-coded)."""
    val = board.get(point, "")
    if val in (BOARD_VAL_PLAYER_1, "player_1"):
        return f"{COLOR_PLAYER_1}(1){COLOR_RESET}" if use_color else "(1)"
    elif val in (BOARD_VAL_PLAYER_2, "player_2"):
        return f"{COLOR_PLAYER_2}(2){COLOR_RESET}" if use_color else "(2)"
    else:
        return "(·)"


def render_board(board: Dict[str, str], use_color: bool = True) -> str:
    """Renders the 24-point Nine Men's Morris board as an ASCII string."""
    c = {p: format_cell(board, p, use_color=use_color) for p in [
        "A1", "A4", "A7",
        "B2", "B4", "B6",
        "C3", "C4", "C5",
        "D1", "D2", "D3", "D5", "D6", "D7",
        "E3", "E4", "E5",
        "F2", "F4", "F6",
        "G1", "G4", "G7"
    ]}

    lines = [
        "    1     2     3     4     5     6     7",
        f"A  {c['A1']}———————————————{c['A4']}———————————————{c['A7']}",
        "    |                 |                 |",
        f"B   |    {c['B2']}—————————{c['B4']}—————————{c['B6']}    |",
        "    |     |           |           |     |",
        f"C   |     |    {c['C3']}———{c['C4']}———{c['C5']}    |     |",
        "    |     |     |           |     |     |",
        f"D  {c['D1']}———{c['D2']}———{c['D3']}         {c['D5']}———{c['D6']}———{c['D7']}",
        "    |     |     |           |     |     |",
        f"E   |     |    {c['E3']}———{c['E4']}———{c['E5']}    |     |",
        "    |     |           |           |     |",
        f"F   |    {c['F2']}—————————{c['F4']}—————————{c['F6']}    |",
        "    |                 |                 |",
        f"G  {c['G1']}———————————————{c['G4']}———————————————{c['G7']}",
    ]
    return "\n".join(lines)


def render_status(
    assigned_id: str,
    opponent_name: str,
    state_payload: Dict[str, str],
    use_color: bool = True,
) -> str:
    """Formats game status summary."""
    p1_unplaced = state_payload.get("player_1_unplaced", 0)
    p1_elim = state_payload.get("player_1_eliminated", 0)
    p2_unplaced = state_payload.get("player_2_unplaced", 0)
    p2_elim = state_payload.get("player_2_eliminated", 0)
    next_turn = state_payload.get("next_turn", "")

    turn_indicator = ">>> YOUR TURN <<<" if next_turn == assigned_id else "Waiting for opponent..."
    p1_label = f"{COLOR_PLAYER_1}Player 1 (1){COLOR_RESET}" if use_color else "Player 1 (1)"
    p2_label = f"{COLOR_PLAYER_2}Player 2 (2){COLOR_RESET}" if use_color else "Player 2 (2)"

    summary = [
        f"You are: {assigned_id} | Opponent: {opponent_name}",
        f"{p1_label}: Unplaced = {p1_unplaced}, Eliminated = {p1_elim}",
        f"{p2_label}: Unplaced = {p2_unplaced}, Eliminated = {p2_elim}",
        f"Active Turn: {next_turn} ({turn_indicator})",
    ]
    return "\n".join(summary)
