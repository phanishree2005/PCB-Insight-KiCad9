"""KiCad Native DRC Runner & Output Parser.

Executes 'kicad-cli pcb drc --format json' safely as a subprocess,
captures authoritative design rule violations, and converts them into
normalized AnalysisFinding instances.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

from pcb_insight.core.data_models import AnalysisFinding, FindingSeverity
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


class NativeDRCRunner:
    """Wrapper around kicad-cli for running authoritative native KiCad DRC."""

    def __init__(self, cli_path: Optional[str] = None):
        self._cli_path = cli_path or self._discover_cli()

    def _discover_cli(self) -> Optional[str]:
        """Discovers kicad-cli executable from PATH or common Windows installations."""
        found = shutil.which("kicad-cli")
        if found:
            return found

        # Check standard Windows directories
        candidates = [
            Path("C:/Program Files/KiCad/9.0/bin/kicad-cli.exe"),
            Path("C:/Program Files/KiCad/bin/kicad-cli.exe"),
            Path("C:/Program Files/KiCad/8.0/bin/kicad-cli.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    @property
    def is_available(self) -> bool:
        return self._cli_path is not None

    def run_drc(self, board_file: Union[str, Path]) -> Tuple[List[AnalysisFinding], Optional[str]]:
        """Executes kicad-cli pcb drc on the board file and parses the JSON report.
        
        Returns:
            Tuple of (List[AnalysisFinding], raw_output_str)
        """
        board_path = Path(board_file).resolve()
        if not board_path.exists():
            raise FileNotFoundError(f"Board file for DRC not found: {board_path}")

        if not self.is_available:
            logger.info("kicad-cli not found on PATH or via discovery. Skipping native DRC execution.")
            return [], None

        logger.info(f"Executing KiCad native DRC via: {self._cli_path}")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            report_path = Path(tmp_file.name)

        try:
            cmd = [
                str(self._cli_path),
                "pcb",
                "drc",
                "--format", "json",
                "--output", str(report_path),
                "--severity-all",
                str(board_path)
            ]
            
            # Execute subprocess safely with explicit arguments (no shell=True)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            raw_stdout = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")

            # If report file was generated, parse it
            if report_path.exists() and report_path.stat().st_size > 0:
                findings = self.parse_json_report(report_path)
                return findings, raw_stdout
            else:
                logger.warning(f"DRC did not produce JSON output file. CLI output: {raw_stdout}")
                return [], raw_stdout

        except subprocess.TimeoutExpired:
            logger.error("kicad-cli pcb drc timed out after 60 seconds.")
            return [], "TimeoutExpired"
        except Exception as e:
            logger.error(f"Error executing native KiCad DRC: {e}")
            return [], str(e)
        finally:
            if report_path.exists():
                try:
                    report_path.unlink()
                except OSError:
                    pass

    def parse_json_report(self, report_path: Path) -> List[AnalysisFinding]:
        """Parses KiCad 8/9/10 JSON DRC report into AnalysisFinding list."""
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse KiCad DRC JSON output: {e}")
            return []

        findings: List[AnalysisFinding] = []

        # 1. Parse Violations
        for v in data.get("violations", []):
            desc = v.get("description", "Design Rule Violation")
            v_type = v.get("type", "drc_violation")
            sev_str = v.get("severity", "error").lower()
            severity = FindingSeverity.ERROR if sev_str == "error" else FindingSeverity.WARNING

            affected_items = []
            for item in v.get("items", []):
                t = item.get("text", "")
                if t:
                    affected_items.append(t)

            findings.append(AnalysisFinding(
                rule_id=f"KICAD-DRC-{v_type.upper().replace(' ', '_')}",
                rule_name=f"Native DRC: {v_type.replace('_', ' ').title()}",
                severity=severity,
                title=desc,
                explanation=f"KiCad native DRC reported violation of type '{v_type}'.",
                remediation="Inspect coordinates in KiCad PCB Editor and adjust trace geometry or clearances.",
                affected_components=[i for i in affected_items if "of " in i],
                source="KiCad_Native_DRC",
                raw_data=v,
            ))

        # 2. Parse Unconnected Items
        for u in data.get("unconnected_items", []):
            desc = u.get("description", "Unconnected Item")
            findings.append(AnalysisFinding(
                rule_id="KICAD-DRC-UNCONNECTED",
                rule_name="Native DRC: Unconnected Items",
                severity=FindingSeverity.ERROR,
                title=desc,
                explanation="KiCad native DRC detected unrouted ratsnest lines between electrical pads.",
                remediation="Complete routing of missing copper traces in PCB Editor.",
                source="KiCad_Native_DRC",
                raw_data=u,
            ))

        return findings
