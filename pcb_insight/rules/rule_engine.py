"""Quality Rule Engine and Orchestration Pipeline.

Maintains registered rule classes, evaluates them sequentially against extracted
board models and analyzer reports, and aggregates all findings.
"""

import time
from datetime import datetime, timezone
from typing import List, Optional

from pcb_insight.analyzers.component_analyzer import ComponentAnalyzer
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalyzer
from pcb_insight.core.data_models import AnalysisFinding, AnalysisResult, BoardData
from pcb_insight.rules.base_rule import BaseRule
from pcb_insight.rules.component_rules import (
    DuplicateReferenceRule,
    MissingFootprintRule,
    MissingReferenceRule,
    MissingValueRule,
    PlaceholderReferenceRule,
    UnassignedFootprintRule,
)
from pcb_insight.rules.connectivity_rules import (
    EmptyNetRule,
    SinglePinNetRule,
    UnassignedElectricalPadRule,
)
from pcb_insight.rules.geometry_rules import MissingBoardOutlineRule, UnroutedBoardRule
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


class RuleEngine:
    """Manages and executes the extensible suite of PCB quality rules."""

    def __init__(self, rules: Optional[List[BaseRule]] = None):
        if rules is not None:
            self._rules = list(rules)
        else:
            self._rules = self._get_default_rules()

    def _get_default_rules(self) -> List[BaseRule]:
        return [
            MissingReferenceRule(),
            DuplicateReferenceRule(),
            MissingValueRule(),
            UnassignedFootprintRule(),
            PlaceholderReferenceRule(),
            SinglePinNetRule(),
            EmptyNetRule(),
            UnassignedElectricalPadRule(),
            MissingBoardOutlineRule(),
            UnroutedBoardRule(),
        ]

    def register_rule(self, rule: BaseRule):
        """Adds a new rule to the engine."""
        self._rules.append(rule)

    @property
    def registered_rules(self) -> List[BaseRule]:
        return list(self._rules)

    def evaluate_board(self, board: BoardData, drc_findings: Optional[List[AnalysisFinding]] = None) -> AnalysisResult:
        """Executes all analyzers and registered rules against the board."""
        start_time = time.perf_counter()
        logger.info(f"Evaluating {len(self._rules)} rules on board '{board.name}'...")

        # 1. Run Component Analyzer
        comp_analyzer = ComponentAnalyzer(board)
        comp_report = comp_analyzer.analyze()

        # 2. Run Connectivity Analyzer
        conn_analyzer = ConnectivityAnalyzer(board)
        conn_report = conn_analyzer.analyze()

        # 3. Evaluate Rule Suite
        all_findings: List[AnalysisFinding] = []
        for rule in self._rules:
            try:
                rule_findings = rule.evaluate(board, comp_report, conn_report)
                all_findings.extend(rule_findings)
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.rule_id}': {e}", exc_info=True)

        # 4. Integrate Native DRC Findings if present
        if drc_findings:
            all_findings.extend(drc_findings)

        elapsed = time.perf_counter() - start_time
        now_iso = datetime.now(timezone.utc).isoformat()

        logger.info(f"Evaluation complete in {elapsed:.3f}s: {len(all_findings)} findings produced.")

        return AnalysisResult(
            board=board,
            findings=all_findings,
            execution_time_seconds=round(elapsed, 4),
            timestamp_iso=now_iso,
            native_drc_executed=bool(drc_findings is not None and len(drc_findings) > 0),
        )
