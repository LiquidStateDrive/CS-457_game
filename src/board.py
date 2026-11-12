"""Board definitions, coordinates, adjacency graph, and mill lines for Nine Men's Morris."""

from typing import Dict, List, Set, Tuple

POINTS: List[str] = [
    "A1", "A4", "A7",
    "B2", "B4", "B6",
    "C3", "C4", "C5",
    "D1", "D2", "D3", "D5", "D6", "D7",
    "E3", "E4", "E5",
    "F2", "F4", "F6",
    "G1", "G4", "G7",
]

MILLS: List[Tuple[str, str, str]] = [
    # 8 Horizontal Mills
    ("A1", "A4", "A7"),
    ("B2", "B4", "B6"),
    ("C3", "C4", "C5"),
    ("D1", "D2", "D3"),
    ("D5", "D6", "D7"),
    ("E3", "E4", "E5"),
    ("F2", "F4", "F6"),
    ("G1", "G4", "G7"),
    # 8 Vertical Mills
    ("A1", "D1", "G1"),
    ("B2", "D2", "F2"),
    ("C3", "D3", "E3"),
    ("A4", "B4", "C4"),
    ("E4", "F4", "G4"),
    ("C5", "D5", "E5"),
    ("B6", "D6", "F6"),
    ("A7", "D7", "G7"),
]

ADJACENCY: Dict[str, Set[str]] = {
    "A1": {"A4", "D1"},
    "A4": {"A1", "A7", "B4"},
    "A7": {"A4", "D7"},
    "B2": {"B4", "D2"},
    "B4": {"B2", "B6", "A4", "C4"},
    "B6": {"B4", "D6"},
    "C3": {"C4", "D3"},
    "C4": {"C3", "C5", "B4"},
    "C5": {"C4", "D5"},
    "D1": {"A1", "G1", "D2"},
    "D2": {"D1", "D3", "B2", "F2"},
    "D3": {"D2", "C3", "E3"},
    "D5": {"D6", "C5", "E5"},
    "D6": {"D5", "D7", "B6", "F6"},
    "D7": {"D6", "A7", "G7"},
    "E3": {"D3", "E4"},
    "E4": {"E3", "E5", "F4"},
    "E5": {"E4", "D5"},
    "F2": {"D2", "F4"},
    "F4": {"F2", "F6", "E4", "G4"},
    "F6": {"F4", "D6"},
    "G1": {"D1", "G4"},
    "G4": {"G1", "G7", "F4"},
    "G7": {"G4", "D7"},
}


def is_valid_point(point: str) -> bool:
    """Checks whether the given string is one of the 24 valid board points."""
    return point in ADJACENCY


def are_adjacent(p1: str, p2: str) -> bool:
    """Checks whether two points are adjacent on the board grid."""
    return p2 in ADJACENCY.get(p1, set())
