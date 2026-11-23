"""Unit tests for Connectivity Analysis Engine."""

from pathlib import Path
import pytest
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalyzer
from pcb_insight.integration.sexpr_parser import SExprParserAdapter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_clean_board_connectivity():
    adapter = SExprParserAdapter(FIXTURES_DIR / "clean_board.kicad_pcb")
    board = adapter.extract_board_data()

    analyzer = ConnectivityAnalyzer(board)
    report = analyzer.analyze()

    assert report.total_nets >= 4
    assert "GND" in report.ground_nets
    assert "+5V" in report.power_nets
    # TP1 is a testpoint, so single_pin_nets should not flag TP1
    assert len(report.single_pin_nets) == 0
    assert len(report.electrical_unconnected_pads) == 0


def test_faulty_board_connectivity():
    adapter = SExprParserAdapter(FIXTURES_DIR / "faulty_board.kicad_pcb")
    board = adapter.extract_board_data()

    analyzer = ConnectivityAnalyzer(board)
    report = analyzer.analyze()

    # DANG_NET is single-pin net
    assert any(n.name == "DANG_NET" for n in report.single_pin_nets)

    # EMPTY_NET has 0 pads
    assert any(n.name == "EMPTY_NET" for n in report.empty_nets)

    # Q1 pad 3 is unassigned active electrical pad
    assert any(p.parent_reference == "Q1" and p.pad_number == "3" for p in report.electrical_unconnected_pads)
