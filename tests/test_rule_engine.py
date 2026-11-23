"""Unit tests for Rule Engine and Quality Rules."""

from pathlib import Path
import pytest
from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.core.data_models import FindingSeverity
from pcb_insight.rules.rule_engine import RuleEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_clean_board_rule_evaluation():
    engine = AnalysisEngine.from_file(FIXTURES_DIR / "clean_board.kicad_pcb", run_native_drc=False)
    result = engine.run()

    # Clean board should have 0 errors and 0 warnings
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.board.component_count == 7


def test_faulty_board_rule_evaluation():
    engine = AnalysisEngine.from_file(FIXTURES_DIR / "faulty_board.kicad_pcb", run_native_drc=False)
    result = engine.run()

    rule_ids = [f.rule_id for f in result.findings]

    # Verify all expected rules triggered
    assert "RULE-COMP-002" in rule_ids  # Duplicate C1
    assert "RULE-COMP-003" in rule_ids  # Missing value on D1
    assert "RULE-COMP-004" in rule_ids  # Missing footprint on U2
    assert "RULE-COMP-005" in rule_ids  # Placeholder R?
    assert "RULE-CONN-001" in rule_ids  # Single-pin DANG_NET
    assert "RULE-CONN-003" in rule_ids  # Unassigned pad on Q1
    assert "RULE-GEOM-001" in rule_ids  # Missing Edge.Cuts outline

    assert result.error_count >= 4
    assert result.warning_count >= 3
