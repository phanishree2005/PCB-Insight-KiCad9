"""Desktop Graphical User Interface for PCB Insight.

Built using standard Python tkinter & ttk for maximum cross-platform
compatibility without requiring external binary GUI packages like wxPython or PyQt.
"""

import math
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional
import webbrowser
from pathlib import Path

from pcb_insight.core.analysis_engine import AnalysisEngine
from pcb_insight.core.data_models import AnalysisResult, FindingSeverity
from pcb_insight.reporting.csv_exporter import CSVExporter
from pcb_insight.reporting.html_report import generate_html_report
from pcb_insight.reporting.risk_summary import calculate_risk_summary
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


class PCBInsightUI(tk.Tk):
    """Main desktop window for PCB Insight."""

    def __init__(self, file_path: Optional[str] = None):
        super().__init__()
        self.title("PCB Insight – KiCad 9 Design Analyzer")
        self.geometry("980x680")
        self.minsize(800, 500)

        self.file_path = file_path
        self.result: Optional[AnalysisResult] = None

        self._apply_styles()
        self._create_widgets()

        if self.file_path:
            self.run_analysis(self.file_path)
        else:
            # Attempt auto-detection over IPC
            self.run_analysis(None)

    def _apply_styles(self):
        style = ttk.Style(self)
        # Use native 'clam' or 'vista' theme
        available = style.theme_names()
        if "vista" in available and sys.platform == "win32":
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")

        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Subheader.TLabel", font=("Segoe UI", 10), foreground="#64748b")
        style.configure("CardTitle.TLabel", font=("Segoe UI", 9, "bold"), foreground="#475569")
        style.configure("CardVal.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Danger.TLabel", foreground="#dc2626")
        style.configure("Warning.TLabel", foreground="#d97706")
        style.configure("Info.TLabel", foreground="#2563eb")

    def _create_widgets(self):
        # 1. Header Frame
        header = ttk.Frame(self, padding="15 12 15 12")
        header.pack(fill=tk.X)

        title_box = ttk.Frame(header)
        title_box.pack(side=tk.LEFT)
        self.lbl_title = ttk.Label(title_box, text="PCB Insight – Intelligent PCB Design Analyzer", style="Header.TLabel")
        self.lbl_title.pack(anchor=tk.W)
        self.lbl_board = ttk.Label(title_box, text="Board: Auto-detecting...", style="Subheader.TLabel")
        self.lbl_board.pack(anchor=tk.W)

        btn_box = ttk.Frame(header)
        btn_box.pack(side=tk.RIGHT)
        ttk.Button(btn_box, text="Open .kicad_pcb...", command=self._on_open_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="Refresh Analysis", command=lambda: self.run_analysis(self.file_path)).pack(side=tk.LEFT, padx=4)

        # 2. Key Metrics Bar
        self.kpi_frame = ttk.LabelFrame(self, text="  Design Health & Statistics  ", padding="10")
        self.kpi_frame.pack(fill=tk.X, padx=15, pady=5)

        self.kpi_grid = ttk.Frame(self.kpi_frame)
        self.kpi_grid.pack(fill=tk.X)

        self.lbl_errors = self._add_kpi(self.kpi_grid, "ERRORS", "0", 0, "Danger.TLabel")
        self.lbl_warnings = self._add_kpi(self.kpi_grid, "WARNINGS", "0", 1, "Warning.TLabel")
        self.lbl_info = self._add_kpi(self.kpi_grid, "INFO FINDINGS", "0", 2, "Info.TLabel")
        self.lbl_comps = self._add_kpi(self.kpi_grid, "COMPONENTS", "0", 3)
        self.lbl_nets = self._add_kpi(self.kpi_grid, "NETS", "0", 4)
        self.lbl_dims = self._add_kpi(self.kpi_grid, "DIMENSIONS", "—", 5)

        # 3. Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Tab 1: Findings Inspector
        self.tab_findings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_findings, text="  Design Findings  ")
        self._build_findings_tab(self.tab_findings)

        # Tab 2: Components Inventory
        self.tab_components = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_components, text="  Component Inventory  ")
        self._build_components_tab(self.tab_components)

        # Tab 3: Connectivity Matrix
        self.tab_connectivity = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_connectivity, text="  Net Connectivity  ")
        self._build_connectivity_tab(self.tab_connectivity)

        # Tab 4: 2D Board Layout & Wires Visualizer
        self.tab_visualizer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_visualizer, text="  2D Board Layout & Wires  ")
        self._build_visualizer_tab(self.tab_visualizer)

        # 4. Bottom Action Bar
        bottom = ttk.Frame(self, padding="15 8 15 12")
        bottom.pack(fill=tk.X)

        ttk.Button(bottom, text="📊 Generate Standalone HTML Report", command=self._on_generate_html).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="📁 Export CSV Data...", command=self._on_export_csv).pack(side=tk.LEFT, padx=4)
        self.lbl_status = ttk.Label(bottom, text="Ready", style="Subheader.TLabel")
        self.lbl_status.pack(side=tk.RIGHT, padx=4)

    def _add_kpi(self, parent, title: str, val: str, col: int, val_style: str = "CardVal.TLabel") -> ttk.Label:
        box = ttk.Frame(parent, padding="10 4 10 4")
        box.grid(row=0, column=col, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        ttk.Label(box, text=title, style="CardTitle.TLabel").pack(anchor=tk.W)
        lbl = ttk.Label(box, text=val, style=val_style)
        lbl.pack(anchor=tk.W)
        return lbl

    def _build_findings_tab(self, parent):
        pane = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview
        tree_frame = ttk.Frame(pane)
        self.tree_findings = ttk.Treeview(
            tree_frame,
            columns=("severity", "rule_id", "title", "components", "nets"),
            show="headings",
            selectmode="browse",
        )
        self.tree_findings.heading("severity", text="Severity")
        self.tree_findings.heading("rule_id", text="Rule ID")
        self.tree_findings.heading("title", text="Title")
        self.tree_findings.heading("components", text="Affected Refs")
        self.tree_findings.heading("nets", text="Affected Nets")

        self.tree_findings.column("severity", width=80, anchor=tk.CENTER)
        self.tree_findings.column("rule_id", width=120)
        self.tree_findings.column("title", width=400)
        self.tree_findings.column("components", width=100)
        self.tree_findings.column("nets", width=100)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_findings.yview)
        self.tree_findings.configure(yscroll=sb.set)
        self.tree_findings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        pane.add(tree_frame, weight=3)

        # Detail Box
        detail_frame = ttk.LabelFrame(pane, text="  Finding Details & Recommended Fix  ", padding="8")
        self.txt_detail = tk.Text(detail_frame, height=5, wrap=tk.WORD, font=("Segoe UI", 9))
        self.txt_detail.pack(fill=tk.BOTH, expand=True)
        pane.add(detail_frame, weight=1)

        self.tree_findings.bind("<<TreeviewSelect>>", self._on_finding_select)

    def _build_components_tab(self, parent):
        tree_frame = ttk.Frame(parent, padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree_comps = ttk.Treeview(
            tree_frame,
            columns=("ref", "val", "footprint", "layer", "pos", "pads"),
            show="headings",
        )
        self.tree_comps.heading("ref", text="Reference")
        self.tree_comps.heading("val", text="Value")
        self.tree_comps.heading("footprint", text="Footprint")
        self.tree_comps.heading("layer", text="Layer")
        self.tree_comps.heading("pos", text="Position (X, Y mm)")
        self.tree_comps.heading("pads", text="Pads")

        self.tree_comps.column("ref", width=90)
        self.tree_comps.column("val", width=120)
        self.tree_comps.column("footprint", width=300)
        self.tree_comps.column("layer", width=80)
        self.tree_comps.column("pos", width=130)
        self.tree_comps.column("pads", width=60, anchor=tk.CENTER)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_comps.yview)
        self.tree_comps.configure(yscroll=sb.set)
        self.tree_comps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_connectivity_tab(self, parent):
        tree_frame = ttk.Frame(parent, padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree_nets = ttk.Treeview(
            tree_frame,
            columns=("name", "code", "type", "pads_count", "pins"),
            show="headings",
        )
        self.tree_nets.heading("name", text="Net Name")
        self.tree_nets.heading("code", text="Code")
        self.tree_nets.heading("type", text="Type")
        self.tree_nets.heading("pads_count", text="Pads")
        self.tree_nets.heading("pins", text="Connected Pins")

        self.tree_nets.column("name", width=220)
        self.tree_nets.column("code", width=60, anchor=tk.CENTER)
        self.tree_nets.column("type", width=90, anchor=tk.CENTER)
        self.tree_nets.column("pads_count", width=60, anchor=tk.CENTER)
        self.tree_nets.column("pins", width=400)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_nets.yview)
        self.tree_nets.configure(yscroll=sb.set)
        self.tree_nets.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_visualizer_tab(self, parent):
        top_bar = ttk.Frame(parent, padding="8 4 8 4")
        top_bar.pack(fill=tk.X)

        ttk.Label(top_bar, text="Legend: ", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(top_bar, text="■ Edge.Cuts (Outline) ", foreground="#eab308").pack(side=tk.LEFT, padx=3)
        ttk.Label(top_bar, text="■ F.Cu Tracks (Wires) ", foreground="#ef4444").pack(side=tk.LEFT, padx=3)
        ttk.Label(top_bar, text="■ B.Cu Tracks ", foreground="#06b6d4").pack(side=tk.LEFT, padx=3)
        ttk.Label(top_bar, text="■ Vias ", foreground="#f59e0b").pack(side=tk.LEFT, padx=3)
        ttk.Label(top_bar, text="·· Ratsnest Airwires ", foreground="#38bdf8").pack(side=tk.LEFT, padx=3)
        ttk.Button(top_bar, text="Redraw", command=self._render_canvas).pack(side=tk.RIGHT, padx=4)

        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._render_canvas())

    def _render_canvas(self):
        if not self.result or not hasattr(self, "canvas"):
            return
        canvas = self.canvas
        canvas.delete("all")

        board = self.result.board
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 50:
            cw = 800
        if ch < 50:
            ch = 500

        coords_x = []
        coords_y = []

        if board.has_edge_cuts and board.bounding_box != (0.0, 0.0, 0.0, 0.0):
            coords_x.extend([board.bounding_box[0], board.bounding_box[2]])
            coords_y.extend([board.bounding_box[1], board.bounding_box[3]])

        for c in board.components:
            coords_x.append(c.position_x_mm)
            coords_y.append(c.position_y_mm)
            for p in c.pads:
                coords_x.append(c.position_x_mm + p.position_x_mm)
                coords_y.append(c.position_y_mm + p.position_y_mm)

        for t in board.tracks:
            coords_x.extend([t.start_x_mm, t.end_x_mm])
            coords_y.extend([t.start_y_mm, t.end_y_mm])

        for v in board.vias:
            coords_x.append(v.position_x_mm)
            coords_y.append(v.position_y_mm)

        if not coords_x or not coords_y:
            canvas.create_text(
                cw // 2, ch // 2,
                text="No layout geometry found on board",
                fill="#64748b", font=("Segoe UI", 12)
            )
            return

        min_x, max_x = min(coords_x), max(coords_x)
        min_y, max_y = min(coords_y), max(coords_y)
        bw = max(15.0, max_x - min_x)
        bh = max(15.0, max_y - min_y)

        margin = 50
        scale = min((cw - 2 * margin) / bw, (ch - 2 * margin) / bh)
        offset_x = (cw - bw * scale) / 2
        offset_y = (ch - bh * scale) / 2

        def tx(x):
            return offset_x + (x - min_x) * scale

        def ty(y):
            return offset_y + (y - min_y) * scale

        # Grid lines
        grid_step = 10.0
        gx = math.floor(min_x / grid_step) * grid_step
        while gx <= max_x + grid_step:
            canvas.create_line(tx(gx), 0, tx(gx), ch, fill="#1e293b", dash=(1, 5))
            gx += grid_step

        gy = math.floor(min_y / grid_step) * grid_step
        while gy <= max_y + grid_step:
            canvas.create_line(0, ty(gy), cw, ty(gy), fill="#1e293b", dash=(1, 5))
            gy += grid_step

        # 1. Edge.Cuts Outline
        if board.has_edge_cuts:
            bx1, by1 = tx(board.bounding_box[0]), ty(board.bounding_box[1])
            bx2, by2 = tx(board.bounding_box[2]), ty(board.bounding_box[3])
            canvas.create_rectangle(bx1, by1, bx2, by2, outline="#facc15", width=2)
            canvas.create_text(
                bx1 + 10, by1 + 10,
                text=f"Edge.Cuts Boundary: {board.dimensions_display}",
                fill="#facc15", anchor="nw", font=("Segoe UI", 8)
            )
        else:
            canvas.create_text(
                20, 20,
                text="⚠ Edge.Cuts Boundary: Not available – board outline missing",
                fill="#f87171", anchor="nw", font=("Segoe UI", 9, "bold")
            )

        # 2. Routed Tracks (Copper Wires)
        for t in board.tracks:
            color = "#ef4444" if "F.Cu" in t.layer else "#06b6d4"
            w = max(2, int(t.width_mm * scale))
            canvas.create_line(tx(t.start_x_mm), ty(t.start_y_mm), tx(t.end_x_mm), ty(t.end_y_mm), fill=color, width=w, capstyle=tk.ROUND)

        # 3. Vias
        for v in board.vias:
            vx, vy = tx(v.position_x_mm), ty(v.position_y_mm)
            r = max(5, int(v.size_mm * scale / 2))
            canvas.create_oval(vx - r, vy - r, vx + r, vy + r, fill="#f59e0b", outline="#fbbf24", width=1)
            dr = max(2, int(v.drill_mm * scale / 2))
            canvas.create_oval(vx - dr, vy - dr, vx + dr, vy + dr, fill="#0f172a", outline="#f59e0b", width=1)

        # 4. Components & Pads
        pad_positions = {}
        for c in board.components:
            cx, cy = tx(c.position_x_mm), ty(c.position_y_mm)

            fw = max(22, int(10.0 * scale))
            fh = max(22, int(8.0 * scale))
            canvas.create_rectangle(cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2, outline="#475569", fill="#1e293b", width=1)
            canvas.create_text(cx, cy - fh / 2 - 9, text=c.reference, fill="#f8fafc", font=("Segoe UI", 9, "bold"))
            if c.value:
                canvas.create_text(cx, cy + fh / 2 + 9, text=c.value, fill="#94a3b8", font=("Segoe UI", 8))

            for p in c.pads:
                px = tx(c.position_x_mm + p.position_x_mm)
                py = ty(c.position_y_mm + p.position_y_mm)
                pad_positions[(c.reference, p.pad_number)] = (px, py)
                pw = max(6, int((p.size_x_mm or 1.2) * scale))
                ph = max(6, int((p.size_y_mm or 1.2) * scale))

                pcolor = "#fbbf24" if p.pad_type == "THRU_HOLE" else ("#f87171" if "F.Cu" in p.layers else "#38bdf8")
                canvas.create_rectangle(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2, fill=pcolor, outline="#ffffff", width=1)
                canvas.create_text(px, py, text=p.pad_number, fill="#0f172a", font=("Segoe UI", 7, "bold"))

        # 5. Ratsnest Airwires (Unrouted Net Connections)
        for net_name, net in board.nets.items():
            if net.pad_count >= 2:
                points = [pad_positions[key] for key in net.pads if key in pad_positions]
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i + 1]
                    canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#38bdf8", dash=(3, 3), width=1)

    def run_analysis(self, file_path: Optional[str]):
        """Executes the analysis engine and populates all UI components."""
        self.lbl_status.config(text="Analyzing board...")
        self.update_idletasks()

        try:
            engine = AnalysisEngine.from_auto(file_path=file_path)
            self.result = engine.run()
            self._populate_ui(self.result)
            self.lbl_status.config(text=f"Analysis completed in {self.result.execution_time_seconds:.3f}s")
        except Exception as e:
            logger.warning(f"Analysis failed or no live board: {e}")
            self.lbl_status.config(text="No active board. Open a .kicad_pcb file.")
            if file_path:
                messagebox.showerror("Analysis Error", f"Failed to analyze board:\n{e}")

    def _populate_ui(self, result: AnalysisResult):
        board = result.board
        self.lbl_board.config(text=f"Board: {board.name} ({board.file_path or 'Live KiCad Session'})")

        # Update KPIs
        self.lbl_errors.config(text=str(result.error_count))
        self.lbl_warnings.config(text=str(result.warning_count))
        self.lbl_info.config(text=str(result.info_count))
        self.lbl_comps.config(text=str(board.component_count))
        self.lbl_nets.config(text=str(board.net_count))
        self.lbl_dims.config(text=board.dimensions_display)

        # Populate Findings Tree
        self.tree_findings.delete(*self.tree_findings.get_children())
        for f in result.findings:
            comps = ", ".join(f.affected_components)
            nets = ", ".join(f.affected_nets)
            self.tree_findings.insert(
                "",
                tk.END,
                values=(f.severity.value.upper(), f.rule_id, f.title, comps, nets),
                tags=(f.severity.value,),
            )
        self.tree_findings.tag_configure("error", foreground="#dc2626")
        self.tree_findings.tag_configure("warning", foreground="#d97706")
        self.tree_findings.tag_configure("info", foreground="#2563eb")

        # Populate Components Tree
        self.tree_comps.delete(*self.tree_comps.get_children())
        for c in board.components:
            pos_str = f"{c.position_x_mm:.2f}, {c.position_y_mm:.2f}"
            self.tree_comps.insert(
                "",
                tk.END,
                values=(c.reference, c.value, c.footprint_name, c.layer, pos_str, c.pad_count),
            )

        # Populate Nets Tree
        self.tree_nets.delete(*self.tree_nets.get_children())
        for name, net in board.nets.items():
            type_str = "Power" if net.is_power else ("Ground" if net.is_ground else "Signal")
            pins_str = ", ".join([f"{r}.{p}" for r, p in net.pads[:8]])
            self.tree_nets.insert(
                "",
                tk.END,
                values=(name, net.code, type_str, net.pad_count, pins_str),
            )

        # Render 2D Board Canvas
        self._render_canvas()

    def _on_finding_select(self, event):
        sel = self.tree_findings.selection()
        if not sel or not self.result:
            return
        idx = self.tree_findings.index(sel[0])
        if idx < len(self.result.findings):
            f = self.result.findings[idx]
            self.txt_detail.delete("1.0", tk.END)
            self.txt_detail.insert(tk.END, f"RULE: {f.rule_id} – {f.rule_name} [{f.severity.value.upper()}]\n")
            self.txt_detail.insert(tk.END, f"TITLE: {f.title}\n\n")
            self.txt_detail.insert(tk.END, f"EXPLANATION:\n{f.explanation}\n\n")
            self.txt_detail.insert(tk.END, f"SUGGESTED ACTION:\n{f.remediation}\n")

    def _on_open_file(self):
        filetypes = [("KiCad PCB Files", "*.kicad_pcb"), ("All Files", "*.*")]
        chosen = filedialog.askopenfilename(title="Select KiCad PCB Layout", filetypes=filetypes)
        if chosen:
            self.file_path = chosen
            self.run_analysis(chosen)

    def _on_generate_html(self):
        if not self.result:
            messagebox.showwarning("No Data", "Please load and analyze a PCB first.")
            return

        out_path = Path("reports/analysis_report.html").resolve()
        generate_html_report(self.result, out_path)
        webbrowser.open(str(out_path))
        messagebox.showinfo("Report Generated", f"HTML Engineering report generated:\n{out_path}")

    def _on_export_csv(self):
        if not self.result:
            messagebox.showwarning("No Data", "Please load and analyze a PCB first.")
            return

        chosen_dir = filedialog.askdirectory(title="Select Folder to Save CSV Reports")
        if chosen_dir:
            dir_path = Path(chosen_dir)
            exporter = CSVExporter(self.result)
            f1 = exporter.export_components(dir_path / "components_inventory.csv")
            f2 = exporter.export_findings(dir_path / "findings_log.csv")
            f3 = exporter.export_connectivity(dir_path / "connectivity_summary.csv")
            messagebox.showinfo("Export Successful", f"Exported 3 CSV reports to:\n{dir_path}")
