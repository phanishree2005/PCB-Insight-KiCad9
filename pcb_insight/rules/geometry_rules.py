"""Board geometry, stackup, and physical integrity rules."""

from typing import List

from pcb_insight.analyzers.component_analyzer import ComponentAnalysisReport
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalysisReport
from pcb_insight.core.data_models import AnalysisFinding, BoardData, FindingSeverity
from pcb_insight.rules.base_rule import BaseRule


class MissingBoardOutlineRule(BaseRule):
    """Checks if the board has a valid physical outline defined on the Edge.Cuts layer."""

    @property
    def rule_id(self) -> str:
        return "RULE-GEOM-001"

    @property
    def name(self) -> str:
        return "Missing Board Outline (Edge.Cuts)"

    @property
    def description(self) -> str:
        return "Verifies that closed geometry exists on the Edge.Cuts layer to define the PCB contour."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.ERROR

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        if not board.has_edge_cuts or board.dimensions_mm == (0.0, 0.0):
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title="No board outline detected on Edge.Cuts layer.",
                explanation="A PCB must have a closed continuous boundary drawn on the Edge.Cuts layer. Without it, board dimensions cannot be calculated and CAM milling machines cannot route the board outline.",
                remediation="Select the Edge.Cuts layer in KiCad and draw a closed rectangular or polygon boundary around your layout.",
            ))
        return findings


class UnroutedBoardRule(BaseRule):
    """Checks if a board has components and nets but zero routed copper tracks."""

    @property
    def rule_id(self) -> str:
        return "RULE-GEOM-002"

    @property
    def name(self) -> str:
        return "Zero Copper Tracks Routed"

    @property
    def description(self) -> str:
        return "Detects when a board layout has components placed but zero conductive tracks routed."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.INFO

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        if board.component_count > 1 and board.track_count == 0:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Board has {board.component_count} components placed but 0 copper tracks routed.",
                explanation="The PCB layout appears to be in early placement stage with no copper tracks routed yet.",
                remediation="Route nets using Route > Single Track (X) in KiCad PCB Editor.",
            ))
        return findings
