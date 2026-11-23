"""Electrical connectivity and net topology rules."""

from typing import List

from pcb_insight.analyzers.component_analyzer import ComponentAnalysisReport
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalysisReport
from pcb_insight.core.data_models import AnalysisFinding, BoardData, FindingSeverity
from pcb_insight.rules.base_rule import BaseRule


class SinglePinNetRule(BaseRule):
    """Checks for electrical nets connected to exactly one component pad."""

    @property
    def rule_id(self) -> str:
        return "RULE-CONN-001"

    @property
    def name(self) -> str:
        return "Single-Pin Net (Antenna / Stub Risk)"

    @property
    def description(self) -> str:
        return "Identifies electrical nets connected to only one physical pad, which act as antenna stubs or reflect incomplete wiring."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.WARNING

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for net in conn_report.single_pin_nets:
            ref, pad_num = net.pads[0] if net.pads else ("Unknown", "1")
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Net '{net.name}' is connected to only 1 pad ({ref} pin {pad_num}).",
                explanation=f"A net with only one connection cannot form a closed electrical circuit. In high-frequency designs, dangling stubs act as quarter-wave resonant antennas radiating EMI.",
                remediation=f"Verify if net '{net.name}' is missing a destination pin in the schematic or delete the dangling net label.",
                affected_components=[ref],
                affected_nets=[net.name],
            ))
        return findings


class EmptyNetRule(BaseRule):
    """Checks for defined nets that contain zero assigned pads."""

    @property
    def rule_id(self) -> str:
        return "RULE-CONN-002"

    @property
    def name(self) -> str:
        return "Empty Net Definition"

    @property
    def description(self) -> str:
        return "Identifies nets declared in the netlist but having 0 physical pad connections on the board."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.INFO

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for net in conn_report.empty_nets:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Net '{net.name}' has 0 assigned pads.",
                explanation="The net is declared in the PCB netlist but no component pads are connected to it. This typically occurs after deleting components without cleaning up nets.",
                remediation="Perform Tools > Update PCB from Schematic to remove unused net declarations.",
                affected_nets=[net.name],
            ))
        return findings


class UnassignedElectricalPadRule(BaseRule):
    """Checks for active electrical pads (SMD/PTH) that have no net connection."""

    @property
    def rule_id(self) -> str:
        return "RULE-CONN-003"

    @property
    def name(self) -> str:
        return "Unassigned Electrical Pad"

    @property
    def description(self) -> str:
        return "Identifies active electrical pins on components that lack an electrical net assignment."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.WARNING

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for pad in conn_report.electrical_unconnected_pads:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Pad {pad.pad_number} of '{pad.parent_reference}' has no net assignment.",
                explanation=f"Electrical pad {pad.pad_number} on '{pad.parent_reference}' is unassigned. If this pin is an active signal or supply pin, it is currently disconnected.",
                remediation=f"Verify schematic connections for '{pad.parent_reference}' pin {pad.pad_number} or explicitly place a No-Connect (NC) flag in the schematic.",
                affected_components=[pad.parent_reference],
            ))
        return findings
