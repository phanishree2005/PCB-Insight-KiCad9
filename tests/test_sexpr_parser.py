"""Unit tests for S-expression parser against real test fixtures."""

from pathlib import Path
import pytest
from pcb_insight.integration.sexpr_parser import SExprParserAdapter, tokenize_sexpr, parse_sexpr_tokens

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_sexpr_tokenizer_and_parser():
    sample = '(kicad_pcb (version 20240108) (net 1 "GND") (footprint "R_0805" (at 10.0 20.0)))'
    tokens = tokenize_sexpr(sample)
    assert len(tokens) > 5
    assert tokens[0] == "("

    tree = parse_sexpr_tokens(tokens)
    assert tree[0] == "kicad_pcb"
    assert tree[1] == ["version", "20240108"]


def test_parse_clean_board_fixture():
    clean_pcb = FIXTURES_DIR / "clean_board.kicad_pcb"
    assert clean_pcb.exists()

    adapter = SExprParserAdapter(clean_pcb)
    assert adapter.is_available() is True

    board = adapter.extract_board_data()
    assert board.name == "clean_board"
    assert board.component_count == 7  # R1, R2, C1, C2, U1, J1, TP1
    assert board.has_edge_cuts is True
    assert board.dimensions_mm[0] > 0.0
    assert board.dimensions_mm[1] > 0.0
    assert board.track_count == 3
    assert board.via_count == 1
    assert "GND" in board.nets
    assert "+5V" in board.nets


def test_parse_faulty_board_fixture():
    faulty_pcb = FIXTURES_DIR / "faulty_board.kicad_pcb"
    assert faulty_pcb.exists()

    adapter = SExprParserAdapter(faulty_pcb)
    board = adapter.extract_board_data()
    assert board.name == "faulty_board"
    assert board.component_count == 6
    assert board.has_edge_cuts is False
    assert board.dimensions_mm == (0.0, 0.0)
    assert "DANG_NET" in board.nets
