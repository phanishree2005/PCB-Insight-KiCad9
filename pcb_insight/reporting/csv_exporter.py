"""RFC 4180 Compliant CSV Exporter for PCB Insight.

Exports component Bill of Materials (BOM), detected findings log,
and electrical connectivity tables into standard CSV format.
"""

import csv
import io
from pathlib import Path
from typing import Union

from pcb_insight.core.data_models import AnalysisResult
from pcb_insight.utils.file_utils import ensure_directory


class CSVExporter:
    """Exports structured analysis tables into comma-separated value files."""

    def __init__(self, result: AnalysisResult):
        self.result = result

    def export_components(self, output_path: Union[str, Path]) -> Path:
        """Exports component inventory table to CSV."""
        path = Path(output_path).resolve()
        ensure_directory(path.parent)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Reference",
                "Value",
                "Prefix",
                "Footprint",
                "Layer",
                "PosX_mm",
                "PosY_mm",
                "Orientation_deg",
                "PadCount",
                "DNP",
            ])
            for c in self.result.board.components:
                writer.writerow([
                    c.reference,
                    c.value,
                    c.prefix,
                    c.footprint_name,
                    c.layer,
                    f"{c.position_x_mm:.3f}",
                    f"{c.position_y_mm:.3f}",
                    f"{c.orientation_deg:.1f}",
                    c.pad_count,
                    "YES" if c.is_dnp else "NO",
                ])
        return path

    def export_findings(self, output_path: Union[str, Path]) -> Path:
        """Exports detected findings log to CSV."""
        path = Path(output_path).resolve()
        ensure_directory(path.parent)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "RuleID",
                "Severity",
                "RuleName",
                "Title",
                "AffectedComponents",
                "AffectedNets",
                "Source",
                "Explanation",
                "Remediation",
            ])
            for finding in self.result.findings:
                writer.writerow([
                    finding.rule_id,
                    finding.severity.value.upper(),
                    finding.rule_name,
                    finding.title,
                    ";".join(finding.affected_components),
                    ";".join(finding.affected_nets),
                    finding.source,
                    finding.explanation,
                    finding.remediation,
                ])
        return path

    def export_connectivity(self, output_path: Union[str, Path]) -> Path:
        """Exports electrical net summary table to CSV."""
        path = Path(output_path).resolve()
        ensure_directory(path.parent)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "NetName",
                "NetCode",
                "PadCount",
                "IsPower",
                "IsGround",
                "ConnectedPads",
            ])
            for name, net in self.result.board.nets.items():
                pads_str = ";".join([f"{ref}.{num}" for ref, num in net.pads])
                writer.writerow([
                    name,
                    net.code,
                    net.pad_count,
                    "YES" if net.is_power else "NO",
                    "YES" if net.is_ground else "NO",
                    pads_str,
                ])
        return path
