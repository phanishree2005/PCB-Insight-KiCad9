"""Unit tests for Component Analysis Engine."""

from pathlib import Path
import pytest
from pcb_insight.analyzers.component_analyzer import ComponentAnalyzer
from pcb_insight.integration.sexpr_parser import SExprParserAdapter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_clean_board_component_analysis():
    adapter = SExprParserAdapter(FIXTURES_DIR / "clean_board.kicad_pcb")
    board = adapter.extract_board_data()

    analyzer = ComponentAnalyzer(board)
    report = analyzer.analyze()

    assert report.total_components == 7
    assert len(report.duplicate_references) == 0
    assert len(report.missing_references) == 0
    assert len(report.placeholder_references) == 0
    assert len(report.missing_values) == 0
    assert len(report.missing_footprints) == 0
    assert "R" in report.prefix_counts
    assert "C" in report.prefix_counts
    assert "U" in report.prefix_counts


def test_faulty_board_component_analysis():
    adapter = SExprParserAdapter(FIXTURES_DIR / "faulty_board.kicad_pcb")
    board = adapter.extract_board_data()

    analyzer = ComponentAnalyzer(board)
    report = analyzer.analyze()

    # Should detect duplicate C1
    assert "C1" in report.duplicate_references
    assert len(report.duplicate_references["C1"]) == 2

    # Should detect placeholder R?
    assert any(c.reference == "R?" for c in report.placeholder_references)

    # Should detect missing value '~' on D1
    assert any(c.reference == "D1" for c in report.missing_values)

    # Should detect missing footprint on U2
    assert any(c.reference == "U2" for c in report.missing_footprints)
