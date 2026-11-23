"""Unit tests for HTML report generator and CSV exporter."""

import tempfile
from pathlib import Path
import pytest
from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.reporting.csv_exporter import CSVExporter
from pcb_insight.reporting.html_report import generate_html_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_html_report_generation():
    engine = AnalysisEngine.from_file(FIXTURES_DIR / "clean_board.kicad_pcb", run_native_drc=False)
    result = engine.run()

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        out_html = Path(tmp.name)

    try:
        report_path = generate_html_report(result, out_html)
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "clean_board" in content
        assert "Design Check Findings" in content
        assert "Component Inventory" in content
    finally:
        if out_html.exists():
            out_html.unlink()


def test_csv_export():
    engine = AnalysisEngine.from_file(FIXTURES_DIR / "faulty_board.kicad_pcb", run_native_drc=False)
    result = engine.run()

    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        exporter = CSVExporter(result)
        
        f_comp = exporter.export_components(dir_path / "components.csv")
        f_find = exporter.export_findings(dir_path / "findings.csv")
        f_conn = exporter.export_connectivity(dir_path / "connectivity.csv")

        assert f_comp.exists() and f_comp.stat().st_size > 0
        assert f_find.exists() and f_find.stat().st_size > 0
        assert f_conn.exists() and f_conn.stat().st_size > 0

        findings_text = f_find.read_text(encoding="utf-8")
        assert "RULE-COMP-002" in findings_text
        assert "RULE-GEOM-001" in findings_text
