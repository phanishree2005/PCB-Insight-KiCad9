"""Comprehensive multi-board dynamic analysis test suite.

Proves that PCB Insight dynamically extracts and evaluates arbitrary KiCad 9
PCB files without hardcoding or sample-specific assumptions.
"""

from pathlib import Path
import pytest
from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.integration.sexpr_parser import SExprParserAdapter
from pcb_insight.reporting.csv_exporter import CSVExporter
from pcb_insight.reporting.html_report import generate_html_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_three_distinct_pcbs_produce_unique_dynamic_outputs(tmp_path):
    """Demonstrates that three distinct boards yield completely distinct models and findings."""
    clean_path = FIXTURES_DIR / "clean_board.kicad_pcb"
    faulty_path = FIXTURES_DIR / "faulty_board.kicad_pcb"
    regulator_path = FIXTURES_DIR / "power_regulator.kicad_pcb"

    assert clean_path.exists()
    assert faulty_path.exists()
    assert regulator_path.exists()

    # 1. Clean 555 Timer Board
    engine_clean = AnalysisEngine.from_file(clean_path, run_native_drc=False)
    res_clean = engine_clean.run()

    # 2. Faulty Unrouted Board
    engine_faulty = AnalysisEngine.from_file(faulty_path, run_native_drc=False)
    res_faulty = engine_faulty.run()

    # 3. Voltage Regulator Board (Different components, nets, and dimensions)
    engine_reg = AnalysisEngine.from_file(regulator_path, run_native_drc=False)
    res_reg = engine_reg.run()

    # --- VERIFY DYNAMIC COMPONENT COUNTS ---
    assert res_clean.board.component_count == 7
    assert res_faulty.board.component_count == 6
    assert res_reg.board.component_count == 8
    assert len({res_clean.board.component_count, res_faulty.board.component_count, res_reg.board.component_count}) == 3

    # --- VERIFY DYNAMIC NET COUNTS & NAMES ---
    assert res_clean.board.net_count == 4
    assert res_faulty.board.net_count == 4
    assert res_reg.board.net_count == 5
    assert "OUT" in res_clean.board.nets
    assert "DANG_NET" in res_faulty.board.nets
    assert "VRAW" in res_reg.board.nets
    assert "VIN" in res_reg.board.nets

    # --- VERIFY DYNAMIC DIMENSIONS & OUTLINES ---
    # Clean: 65.0 x 35.0 mm
    assert res_clean.board.has_edge_cuts is True
    assert res_clean.board.dimensions_mm == (65.0, 35.0)
    assert res_clean.board.dimensions_display == "65.0 × 35.0 mm"

    # Faulty: missing outline
    assert res_faulty.board.has_edge_cuts is False
    assert res_faulty.board.dimensions_mm == (0.0, 0.0)
    assert res_faulty.board.dimensions_display == "Not available – board outline missing"

    # Regulator: 45.0 x 30.0 mm
    assert res_reg.board.has_edge_cuts is True
    assert res_reg.board.dimensions_mm == (45.0, 30.0)
    assert res_reg.board.dimensions_display == "45.0 × 30.0 mm"

    # --- VERIFY DYNAMIC ROUTING & VIAS ---
    assert res_clean.board.track_count == 3
    assert res_clean.board.via_count == 1

    assert res_faulty.board.track_count == 0
    assert res_faulty.board.via_count == 0

    assert res_reg.board.track_count == 5
    assert res_reg.board.via_count == 2

    # --- VERIFY DYNAMIC FINDINGS ---
    # Faulty board must have multiple errors and warnings
    assert res_faulty.error_count == 4
    assert res_faulty.warning_count == 3
    assert res_faulty.info_count == 2

    # Clean board must have 0 errors and 0 warnings
    assert res_clean.error_count == 0
    assert res_clean.warning_count == 0

    # Power regulator board must have 0 errors and 0 warnings
    assert res_reg.error_count == 0
    assert res_reg.warning_count == 0

    # --- VERIFY REPORTS DO NOT HARDCODE BOARD DATA ---
    report_clean = tmp_path / "clean.html"
    generate_html_report(res_clean, report_clean)
    clean_html = report_clean.read_text(encoding="utf-8")
    assert "clean_board" in clean_html
    assert "65.0 × 35.0 mm" in clean_html
    assert "AMS1117" not in clean_html

    report_reg = tmp_path / "regulator.html"
    generate_html_report(res_reg, report_reg)
    reg_html = report_reg.read_text(encoding="utf-8")
    assert "power_regulator" in reg_html
    assert "45.0 × 30.0 mm" in reg_html
    assert "AMS1117-3.3" in reg_html
    assert "NE555P" not in reg_html


def test_empty_board_handling():
    """Verifies that an empty board is handled gracefully without exceptions."""
    empty_path = FIXTURES_DIR / "empty_board.kicad_pcb"
    assert empty_path.exists()

    engine = AnalysisEngine.from_file(empty_path, run_native_drc=False)
    result = engine.run()

    assert result.board.component_count == 0
    assert result.board.net_count == 0
    assert result.board.track_count == 0
    assert result.board.via_count == 0
    assert result.board.has_edge_cuts is False
    assert result.board.dimensions_display == "Not available – board outline missing"

    # Only missing outline rule triggers
    rule_ids = [f.rule_id for f in result.findings]
    assert "RULE-GEOM-001" in rule_ids
    assert "RULE-GEOM-002" not in rule_ids  # Should not trigger unrouted for 0 components
