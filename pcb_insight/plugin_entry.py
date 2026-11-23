"""Command-Line Interface and KiCad Action Plugin Entrypoint for PCB Insight."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from pcb_insight import __version__
from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.reporting.csv_exporter import CSVExporter
from pcb_insight.reporting.html_report import generate_html_report
from pcb_insight.reporting.risk_summary import calculate_risk_summary
from pcb_insight.utils.logging_config import setup_logger

logger = setup_logger()


def main(argv: Optional[list] = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="pcb_insight",
        description="PCB Insight: Intelligent PCB Design Analyzer for KiCad 9",
    )
    parser.add_argument("board_file", nargs="?", help="Path to .kicad_pcb design file")
    parser.add_argument("--html", metavar="PATH", help="Generate standalone HTML report at PATH")
    parser.add_argument("--csv-dir", metavar="DIR", help="Export CSV tables to directory DIR")
    parser.add_argument("--no-gui", action="store_true", help="Run headlessly in CLI without opening GUI")
    parser.add_argument("--no-drc", action="store_true", help="Skip native kicad-cli DRC execution")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)

    # If running headless CLI or export requested
    if args.no_gui or args.html or args.csv_dir:
        try:
            engine = AnalysisEngine.from_auto(file_path=args.board_file, run_native_drc=not args.no_drc)
            result = engine.run()
            risk = calculate_risk_summary(result)

            print("=" * 65)
            print(f" PCB INSIGHT v{__version__} – Design Analysis Report")
            print("=" * 65)
            print(f" Board Name  : {result.board.name}")
            print(f" Dimensions  : {result.board.dimensions_mm[0]} x {result.board.dimensions_mm[1]} mm")
            print(f" Components  : {result.board.component_count}")
            print(f" Nets        : {result.board.net_count}")
            print(f" Tracks/Vias : {result.board.track_count} tracks, {result.board.via_count} vias")
            print("-" * 65)
            print(f" Findings    : {result.total_findings} total")
            print(f"   - Errors  : {result.error_count}")
            print(f"   - Warnings: {result.warning_count}")
            print(f"   - Info    : {result.info_count}")
            print(f" Health      : {risk.health_status}")
            print("=" * 65)

            if result.findings:
                print("\nTop Findings:")
                for f in result.findings[:10]:
                    print(f" [{f.severity.value.upper()}] {f.rule_id}: {f.title}")

            if args.html:
                out_html = generate_html_report(result, args.html)
                print(f"\n[+] HTML report generated at: {out_html}")

            if args.csv_dir:
                csv_dir = Path(args.csv_dir)
                exp = CSVExporter(result)
                exp.export_components(csv_dir / "components.csv")
                exp.export_findings(csv_dir / "findings.csv")
                exp.export_connectivity(csv_dir / "connectivity.csv")
                print(f"[+] CSV tables exported to: {csv_dir}")

            return 0 if result.error_count == 0 else 1

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return 2

    # Otherwise, launch desktop UI
    try:
        from pcb_insight.ui.main_window import PCBInsightUI
        app = PCBInsightUI(file_path=args.board_file)
        app.mainloop()
        return 0
    except Exception as e:
        logger.error(f"Failed to launch UI: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
