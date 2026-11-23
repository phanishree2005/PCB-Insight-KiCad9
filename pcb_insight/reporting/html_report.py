"""Standalone, Offline-Capable HTML Report Generator for PCB Insight.

Renders an interactive, print-ready engineering analysis report with
summary cards, interactive filters, search bars, component inventory,
and detailed explainable findings. Zero external network dependencies.
"""

from datetime import datetime
from pathlib import Path
from typing import Union

from pcb_insight.core.data_models import AnalysisResult, FindingSeverity
from pcb_insight.reporting.risk_summary import calculate_risk_summary
from pcb_insight.utils.file_utils import ensure_directory


def generate_html_report(result: AnalysisResult, output_path: Union[str, Path]) -> Path:
    """Generates a standalone single-file HTML report and writes it to disk."""
    path = Path(output_path).resolve()
    ensure_directory(path.parent)

    risk = calculate_risk_summary(result)
    board = result.board

    # Pre-render rows
    findings_rows = []
    for idx, f in enumerate(result.findings, 1):
        sev_class = f"badge-{f.severity.value}"
        sev_label = f.severity.value.upper()
        comps_str = ", ".join(f.affected_components) if f.affected_components else "—"
        nets_str = ", ".join(f.affected_nets) if f.affected_nets else "—"

        findings_rows.append(f"""
        <tr class="finding-row severity-{f.severity.value}">
            <td><span class="badge {sev_class}">{sev_label}</span></td>
            <td><code>{f.rule_id}</code></td>
            <td>
                <strong>{f.title}</strong>
                <div class="explanation">{f.explanation}</div>
                <div class="remediation"><strong>Fix:</strong> {f.remediation}</div>
            </td>
            <td>{comps_str}</td>
            <td>{nets_str}</td>
        </tr>
        """)

    components_rows = []
    for c in board.components:
        components_rows.append(f"""
        <tr>
            <td><strong>{c.reference}</strong></td>
            <td>{c.value or '<span class="text-muted">~</span>'}</td>
            <td><code>{c.footprint_name}</code></td>
            <td>{c.layer}</td>
            <td>{c.position_x_mm:.2f}, {c.position_y_mm:.2f}</td>
            <td>{c.pad_count}</td>
        </tr>
        """)

    nets_rows = []
    for name, net in list(board.nets.items())[:50]:  # Limit top 50 in table
        type_str = "Power" if net.is_power else ("Ground" if net.is_ground else "Signal")
        nets_rows.append(f"""
        <tr>
            <td><code>{name}</code></td>
            <td>{type_str}</td>
            <td>{net.pad_count}</td>
            <td>{', '.join([f'{r}.{p}' for r, p in net.pads[:6]])}{'...' if len(net.pads) > 6 else ''}</td>
        </tr>
        """)

    status_color = "#dc2626" if risk.error_count > 0 else ("#d97706" if risk.warning_count > 0 else "#16a34a")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PCB Insight Report - {board.name}</title>
<style>
    :root {{
        --primary: #1e293b;
        --secondary: #0ea5e9;
        --bg: #f8fafc;
        --card-bg: #ffffff;
        --text: #0f172a;
        --text-muted: #64748b;
        --border: #e2e8f0;
        --danger: #ef4444;
        --warning: #f59e0b;
        --success: #10b981;
        --info: #3b82f6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--bg);
        color: var(--text);
        line-height: 1.5;
        padding: 24px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
        background: var(--primary);
        color: white;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }}
    header h1 {{ font-size: 24px; font-weight: 700; }}
    header .meta {{ color: #94a3b8; font-size: 14px; }}
    .status-pill {{
        background: {status_color};
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 14px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }}
    .card {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .card h3 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 8px; }}
    .card .value {{ font-size: 26px; font-weight: 700; }}
    .card.error .value {{ color: var(--danger); }}
    .card.warning .value {{ color: var(--warning); }}
    .card.info .value {{ color: var(--info); }}
    .card.success .value {{ color: var(--success); }}

    .section {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 24px;
    }}
    .section h2 {{ font-size: 18px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}

    .toolbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .search-input {{
        padding: 8px 12px;
        border: 1px solid var(--border);
        border-radius: 6px;
        width: 280px;
        font-size: 14px;
    }}
    .btn-group button {{
        background: white;
        border: 1px solid var(--border);
        padding: 6px 12px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.2s;
    }}
    .btn-group button:first-child {{ border-radius: 6px 0 0 6px; }}
    .btn-group button:last-child {{ border-radius: 0 6px 6px 0; }}
    .btn-group button.active {{ background: var(--primary); color: white; border-color: var(--primary); }}

    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: #f1f5f9; font-weight: 600; color: var(--text-muted); }}
    tr:hover {{ background-color: #f8fafc; }}

    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .badge-error {{ background: #fee2e2; color: #991b1b; }}
    .badge-warning {{ background: #fef3c7; color: #92400e; }}
    .badge-info {{ background: #dbeafe; color: #1e40af; }}

    .explanation {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    .remediation {{ font-size: 13px; color: #047857; margin-top: 4px; }}
    .actions-list {{ padding-left: 20px; }}
    .actions-list li {{ margin-bottom: 6px; }}

    @media print {{
        body {{ background: white; padding: 0; }}
        header {{ background: white; color: black; border-bottom: 2px solid #000; border-radius: 0; }}
        .toolbar, .btn-group, .search-input {{ display: none !important; }}
        .section, .card {{ border: 1px solid #ccc; box-shadow: none; break-inside: avoid; }}
    }}
</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>PCB INSIGHT – Engineering Audit Report</h1>
            <div class="meta">Board: <strong>{board.name}</strong> | File: {board.file_path or 'Live KiCad Session'} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
        </div>
        <div>
            <span class="status-pill">{risk.health_status}</span>
        </div>
    </header>

    <!-- Executive KPI Grid -->
    <div class="grid">
        <div class="card error">
            <h3>Errors</h3>
            <div class="value">{risk.error_count}</div>
        </div>
        <div class="card warning">
            <h3>Warnings</h3>
            <div class="value">{risk.warning_count}</div>
        </div>
        <div class="card info">
            <h3>Info Findings</h3>
            <div class="value">{risk.info_count}</div>
        </div>
        <div class="card">
            <h3>Components</h3>
            <div class="value">{board.component_count}</div>
        </div>
        <div class="card">
            <h3>Nets</h3>
            <div class="value">{board.net_count}</div>
        </div>
        <div class="card">
            <h3>Dimensions</h3>
            <div class="value">{board.dimensions_mm[0]} &times; {board.dimensions_mm[1]} mm</div>
        </div>
        <div class="card">
            <h3>Copper Layers</h3>
            <div class="value">{board.copper_layer_count}</div>
        </div>
        <div class="card">
            <h3>Tracks / Vias</h3>
            <div class="value">{board.track_count} / {board.via_count}</div>
        </div>
    </div>

    <!-- Recommended Actions -->
    <div class="section">
        <h2>Recommended Remediation Actions</h2>
        <ul class="actions-list">
            {''.join([f'<li>{a}</li>' for a in risk.recommended_actions])}
        </ul>
    </div>

    <!-- Findings Section -->
    <div class="section">
        <h2>Design Check Findings ({len(result.findings)})</h2>
        <div class="toolbar">
            <div class="btn-group" id="filter-buttons">
                <button class="active" onclick="filterFindings('all')">All ({len(result.findings)})</button>
                <button onclick="filterFindings('error')">Errors ({risk.error_count})</button>
                <button onclick="filterFindings('warning')">Warnings ({risk.warning_count})</button>
                <button onclick="filterFindings('info')">Info ({risk.info_count})</button>
            </div>
            <input type="text" class="search-input" id="search-input" placeholder="Search rule, component, or title..." onkeyup="searchFindings()">
        </div>
        <div style="overflow-x: auto;">
            <table id="findings-table">
                <thead>
                    <tr>
                        <th style="width: 90px;">Severity</th>
                        <th style="width: 140px;">Rule ID</th>
                        <th>Issue Description & Remediation</th>
                        <th style="width: 120px;">Affected Ref</th>
                        <th style="width: 120px;">Affected Net</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(findings_rows) if findings_rows else '<tr><td colspan="5" style="text-align:center; padding: 20px;">No findings reported. Design is clean!</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Component Inventory (BOM) -->
    <div class="section">
        <h2>Component Inventory & Bill of Materials ({board.component_count} parts)</h2>
        <div style="overflow-x: auto; max-height: 400px;">
            <table>
                <thead>
                    <tr>
                        <th>Reference</th>
                        <th>Value</th>
                        <th>Footprint</th>
                        <th>Layer</th>
                        <th>Position (X, Y mm)</th>
                        <th>Pads</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(components_rows) if components_rows else '<tr><td colspan="6">No components found on board.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Net Connectivity Overview -->
    <div class="section">
        <h2>Net Connectivity Overview ({board.net_count} nets)</h2>
        <div style="overflow-x: auto; max-height: 350px;">
            <table>
                <thead>
                    <tr>
                        <th>Net Name</th>
                        <th>Net Type</th>
                        <th>Pads Count</th>
                        <th>Connected Pins</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(nets_rows) if nets_rows else '<tr><td colspan="4">No electrical nets defined.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    function filterFindings(severity) {{
        const rows = document.querySelectorAll('.finding-row');
        const buttons = document.querySelectorAll('#filter-buttons button');
        buttons.forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');

        rows.forEach(row => {{
            if (severity === 'all' || row.classList.contains('severity-' + severity)) {{
                row.style.display = '';
            }} else {{
                row.style.display = 'none';
            }}
        }});
    }}

    function searchFindings() {{
        const input = document.getElementById('search-input').value.toLowerCase();
        const rows = document.querySelectorAll('.finding-row');
        rows.forEach(row => {{
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(input) ? '' : 'none';
        }});
    }}
</script>
</body>
</html>
"""
    path.write_text(html_content, encoding="utf-8")
    return path
