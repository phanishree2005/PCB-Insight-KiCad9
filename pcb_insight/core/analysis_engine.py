"""Top-level Analysis Engine Pipeline Orchestrator.

Orchestrates board data extraction (via IPC, pcbnew, or S-expression file),
executes component and connectivity analyzers, invokes the rule engine,
and optional native DRC.
"""

from pathlib import Path
from typing import Optional, Union

from pcb_insight.core.data_models import AnalysisResult, BoardData
from pcb_insight.integration.adapter_interface import BoardAdapter
from pcb_insight.integration.drc_runner import NativeDRCRunner
from pcb_insight.integration.ipc_adapter import IPCClientAdapter
from pcb_insight.integration.pcbnew_adapter import PcbnewAdapter
from pcb_insight.integration.sexpr_parser import SExprParserAdapter
from pcb_insight.rules.rule_engine import RuleEngine
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


class AnalysisEngine:
    """Coordinates data extraction, rule execution, and finding aggregation."""

    def __init__(
        self,
        adapter: Optional[BoardAdapter] = None,
        rule_engine: Optional[RuleEngine] = None,
        run_native_drc: bool = True,
    ):
        self.adapter = adapter
        self.rule_engine = rule_engine or RuleEngine()
        self.run_native_drc = run_native_drc

    @classmethod
    def from_file(cls, file_path: Union[str, Path], run_native_drc: bool = True) -> "AnalysisEngine":
        """Instantiates an AnalysisEngine using the pure-Python S-expression parser."""
        adapter = SExprParserAdapter(file_path)
        return cls(adapter=adapter, run_native_drc=run_native_drc)

    @classmethod
    def from_ipc(cls, socket_path: Optional[str] = None, run_native_drc: bool = True) -> "AnalysisEngine":
        """Instantiates an AnalysisEngine connected to KiCad 9 over IPC."""
        adapter = IPCClientAdapter(socket_path=socket_path)
        return cls(adapter=adapter, run_native_drc=run_native_drc)

    @classmethod
    def from_auto(cls, file_path: Optional[Union[str, Path]] = None, run_native_drc: bool = True) -> "AnalysisEngine":
        """Auto-discovers the best available adapter (IPC -> pcbnew -> S-expression file)."""
        # 1. If explicit file path is provided, use SExprParserAdapter
        if file_path:
            p = Path(file_path)
            if p.exists() and p.is_file():
                return cls(adapter=SExprParserAdapter(p), run_native_drc=run_native_drc)

        # 2. Try KiCad 9 IPC API
        ipc = IPCClientAdapter()
        if ipc.is_available():
            logger.info("Auto-discovery selected: KiCad 9 IPC API")
            return cls(adapter=ipc, run_native_drc=run_native_drc)

        # 3. Try legacy in-process pcbnew
        swig = PcbnewAdapter()
        if swig.is_available():
            logger.info("Auto-discovery selected: Legacy pcbnew ActionPlugin")
            return cls(adapter=swig, run_native_drc=run_native_drc)

        raise RuntimeError(
            "Could not automatically detect an active KiCad session or valid board file. "
            "Please provide a path to a .kicad_pcb file or ensure KiCad 9 is running with API Server enabled."
        )

    def run(self) -> AnalysisResult:
        """Executes the full extraction and analysis pipeline."""
        if not self.adapter:
            raise ValueError("No BoardAdapter configured for AnalysisEngine.")

        logger.info(f"Starting PCB Insight analysis with adapter: {self.adapter.adapter_name}")
        board_data = self.adapter.extract_board_data()

        drc_findings = []
        if self.run_native_drc and board_data.file_path:
            drc_runner = NativeDRCRunner()
            if drc_runner.is_available:
                findings, _ = drc_runner.run_drc(board_data.file_path)
                drc_findings.extend(findings)

        result = self.rule_engine.evaluate_board(board_data, drc_findings=drc_findings)
        return result
