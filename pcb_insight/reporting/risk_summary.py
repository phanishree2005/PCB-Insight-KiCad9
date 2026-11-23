"""Engineering Risk Summary and Findings Aggregator.

Calculates transparent, explainable design health metrics, hotspot rankings,
and categorized finding distributions without arbitrary or deceptive safety scores.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from pcb_insight.core.data_models import AnalysisFinding, AnalysisResult, FindingSeverity


@dataclass
class RiskSummary:
    """Detailed summary of engineering risks and finding hotspots."""
    total_findings: int
    error_count: int
    warning_count: int
    info_count: int
    health_status: str  # "Critical Issues", "Needs Review", "Clean Design"
    top_affected_components: List[Tuple[str, int]] = field(default_factory=list)
    top_affected_nets: List[Tuple[str, int]] = field(default_factory=list)
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)


def calculate_risk_summary(result: AnalysisResult) -> RiskSummary:
    """Analyzes an AnalysisResult and generates a transparent engineering risk summary."""
    errors = result.error_count
    warnings = result.warning_count
    infos = result.info_count
    total = result.total_findings

    if errors > 0:
        status = "Critical Issues Detected"
    elif warnings > 0:
        status = "Review Recommended"
    else:
        status = "Clean Design"

    # Count affected components and nets
    comp_counter: Counter = Counter()
    net_counter: Counter = Counter()
    category_counter: Counter = Counter()

    for f in result.findings:
        # Category by Rule Prefix
        cat = f.rule_id.split("-")[1] if "-" in f.rule_id else "GENERAL"
        category_counter[cat] += 1

        for comp in f.affected_components:
            comp_counter[comp] += 1
        for net in f.affected_nets:
            net_counter[net] += 1

    actions: List[str] = []
    if errors > 0:
        actions.append(f"Resolve {errors} critical error(s) before attempting manufacturing or Gerber export.")
    if any(f.rule_id == "RULE-GEOM-001" for f in result.findings):
        actions.append("Draw a closed board boundary polygon on the Edge.Cuts layer.")
    if any(f.rule_id == "RULE-COMP-002" for f in result.findings):
        actions.append("Re-annotate duplicate component reference designators in schematic editor.")
    if warnings > 0:
        actions.append(f"Inspect {warnings} design warning(s) to verify intentionality (e.g. single-pin nets, NC pins).")
    if not actions:
        actions.append("Design passed all static sanity checks. Proceed to physical clearance verification.")

    return RiskSummary(
        total_findings=total,
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
        health_status=status,
        top_affected_components=comp_counter.most_common(5),
        top_affected_nets=net_counter.most_common(5),
        findings_by_category=dict(category_counter),
        recommended_actions=actions,
    )
