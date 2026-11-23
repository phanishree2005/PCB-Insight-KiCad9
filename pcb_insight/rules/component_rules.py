"""Component metadata and Bill of Materials quality rules."""

from typing import List

from pcb_insight.analyzers.component_analyzer import ComponentAnalysisReport
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalysisReport
from pcb_insight.core.data_models import AnalysisFinding, BoardData, FindingSeverity
from pcb_insight.rules.base_rule import BaseRule


class MissingReferenceRule(BaseRule):
    """Checks for components with completely empty reference designators."""

    @property
    def rule_id(self) -> str:
        return "RULE-COMP-001"

    @property
    def name(self) -> str:
        return "Missing Component Reference"

    @property
    def description(self) -> str:
        return "Detects footprints that lack a reference designator entirely."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.ERROR

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for c in comp_report.missing_references:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Component at ({c.position_x_mm}, {c.position_y_mm}) has no reference designator.",
                explanation="A footprint exists on the board without an assigned reference designator. This prevents pick-and-place centroid generation and BOM reconciliation.",
                remediation="Open the schematic editor, annotate all components, and update the PCB from schematic (F8).",
                affected_components=[f"Footprint:{c.footprint_name}"],
            ))
        return findings


class DuplicateReferenceRule(BaseRule):
    """Checks for duplicate reference designators sharing the exact same identifier."""

    @property
    def rule_id(self) -> str:
        return "RULE-COMP-002"

    @property
    def name(self) -> str:
        return "Duplicate Reference Designator"

    @property
    def description(self) -> str:
        return "Identifies multiple physical components claiming the exact same reference designator."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.ERROR

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for ref, items in comp_report.duplicate_references.items():
            locs = [f"({item.position_x_mm}, {item.position_y_mm})" for item in items]
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Duplicate reference designator '{ref}' detected ({len(items)} instances).",
                explanation=f"Multiple components share reference '{ref}' at positions: {', '.join(locs)}. This causes netlist mapping collisions and manufacturing halts.",
                remediation="Re-annotate the schematic uniquely and update the PCB.",
                affected_components=[ref],
            ))
        return findings


class MissingValueRule(BaseRule):
    """Checks for components lacking an engineering value (e.g. empty or default '~')."""

    @property
    def rule_id(self) -> str:
        return "RULE-COMP-003"

    @property
    def name(self) -> str:
        return "Missing Component Value"

    @property
    def description(self) -> str:
        return "Detects components with blank or placeholder values (such as '~')."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.WARNING

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for c in comp_report.missing_values:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Component '{c.reference}' has missing or placeholder value ('{c.value or '~'}').",
                explanation="Components must carry meaningful nominal values (e.g. '10k', '100nF', 'LM358') to enable automated Bill of Materials generation and procurement.",
                remediation=f"Assign a valid component value for '{c.reference}' in the schematic.",
                affected_components=[c.reference],
            ))
        return findings


class UnassignedFootprintRule(BaseRule):
    """Checks for components lacking a physical footprint identifier."""

    @property
    def rule_id(self) -> str:
        return "RULE-COMP-004"

    @property
    def name(self) -> str:
        return "Unassigned Footprint"

    @property
    def description(self) -> str:
        return "Detects components that lack an assigned footprint library definition."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.ERROR

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for c in comp_report.missing_footprints:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Component '{c.reference}' has no footprint assigned.",
                explanation="Components without valid footprints cannot be placed or manufactured on the PCB.",
                remediation=f"Assign a footprint from the KiCad Footprint Library for '{c.reference}'.",
                affected_components=[c.reference],
            ))
        return findings


# Alias for backward and naming compatibility
MissingFootprintRule = UnassignedFootprintRule


class PlaceholderReferenceRule(BaseRule):
    """Checks for placeholder or unannotated reference designators (e.g. R?, REF**)."""

    @property
    def rule_id(self) -> str:
        return "RULE-COMP-005"

    @property
    def name(self) -> str:
        return "Placeholder Reference Designator"

    @property
    def description(self) -> str:
        return "Detects components with unannotated question marks ('?') or wildcards ('*')."

    @property
    def severity(self) -> FindingSeverity:
        return FindingSeverity.ERROR

    def evaluate(
        self, board: BoardData, comp_report: ComponentAnalysisReport, conn_report: ConnectivityAnalysisReport
    ) -> List[AnalysisFinding]:
        findings = []
        for c in comp_report.placeholder_references:
            findings.append(AnalysisFinding(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                title=f"Component '{c.reference}' is unannotated or contains wildcard placeholder characters.",
                explanation="References like 'R?' or 'REF**' indicate that schematic annotation was bypassed before updating the board.",
                remediation="Run Tools > Annotate Schematic in the schematic editor and update the PCB.",
                affected_components=[c.reference],
            ))
        return findings
