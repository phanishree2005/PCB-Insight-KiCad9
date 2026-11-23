from http.server import BaseHTTPRequestHandler
from pathlib import Path
import sys

# Ensure repository root is in python path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.reporting.html_report import generate_html_report


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            report_path = root_dir / "reports" / "sample_arduino_dev_board_report.html"
            if report_path.exists():
                html = report_path.read_text(encoding="utf-8")
            else:
                board_path = root_dir / "tests" / "fixtures" / "arduino_dev_board.kicad_pcb"
                engine = AnalysisEngine.from_file(board_path, run_native_drc=False)
                result = engine.run()
                temp_report = Path("/tmp/report.html")
                generate_html_report(result, temp_report)
                html = temp_report.read_text(encoding="utf-8")
        except Exception as e:
            html = f"<html><body><h1>PCB Insight Web Preview</h1><p>Error: {e}</p></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
