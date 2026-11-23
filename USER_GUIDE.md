# PCB Insight – User Guide
**Intelligent PCB Design Analysis & Engineering Reporting for KiCad 9**  
**Document ID:** UG-001  
**Version:** 1.0.0 (Pre-Implementation Draft)

---

## 1. Introduction

**PCB Insight** is an automated design analysis and connectivity auditing plugin for **KiCad 9**. It assists electronics engineers, hardware reviewers, and students by performing automated sanity checks on PCB layouts, auditing component metadata, verifying electrical net integrity, and generating standalone, shareable engineering reports.

---

## 2. Getting Started

### 2.1 Launching PCB Insight inside KiCad 9

1. **Open KiCad 9 PCB Editor:**
   - Launch your project and open your board layout (`.kicad_pcb`).
2. **Ensure API Server is Enabled (for IPC mode):**
   - In KiCad, go to **Preferences → Plugins**.
   - Verify that **Enable API Server** is checked.
3. **Launch the Plugin:**
   - **Method A (Toolbar Icon):** Click the **PCB Insight** icon located on the top action toolbar.
   - **Method B (Menu Bar):** Go to **Tools → External Plugins → PCB Insight**.
   - **Method C (Command Line / Standalone):**
     ```powershell
     python -m pcb_insight "path/to/your_board.kicad_pcb"
     ```

---

## 3. User Interface Overview

When launched, PCB Insight opens a clean, focused engineering dialog divided into tabbed views:

### 3.1 Dashboard & Board Overview
- **Board Summary:** Displays project title, board dimensions ($\text{width} \times \text{height}$ in mm), copper layer count, and active layers.
- **Complexity Metrics:** Total component count, total net count, track count, via count, and copper zone count.
- **Quality Status Cards:** High-level summary of detected design findings categorized by severity:
  - 🔴 **Errors:** Critical items requiring immediate remediation (e.g. duplicate designators, missing board outline).
  - 🟡 **Warnings:** Potential design flaws (e.g. single-pin nets, missing component values).
  - 🔵 **Information:** Design observations (e.g. non-plated mounting holes, test points).

### 3.2 Component Analysis Tab
- **Inventory Table:** Sortable list of all components with Reference, Value, Footprint, Board Layer, and Placement Coordinates ($X, Y$).
- **Prefix Breakdown:** Components grouped by IEEE 315 prefix (`R`, `C`, `U`, `D`, `Q`, `J`, etc.).
- **Metadata Hygiene Warnings:** Highlights components with missing values (`~`), placeholder designators (`R?`), or unassigned footprints.

### 3.3 Connectivity Analysis Tab
- **Net-to-Pad Topology:** Interactive matrix of all electrical nets and their assigned component pins.
- **Single-Pin Net Inspector:** Lists nets with exactly one assigned pad, alerting the designer to dangling antenna stubs or broken net connections.
- **Unassigned Pad Audit:** Lists pads without a net code, distinguishing active electrical pads (PTH/SMD) from mechanical mounting holes (NPTH).

### 3.4 DRC Results Tab
- Displays authoritative design rule violations parsed from KiCad's native Design Rules Checker (`kicad-cli pcb drc`).
- Shows clearance violations, unconnected items, and footprint parity warnings directly linked to KiCad's native solver.

---

## 4. Generating Reports & Data Exports

PCB Insight provides two primary export functions:

### 4.1 Standalone HTML Engineering Report
1. Click **Generate HTML Report** in the plugin window.
2. The report is compiled into a single, self-contained HTML file (including inline responsive CSS and interactive JavaScript tables).
3. The report automatically opens in your default web browser and can be printed or saved as a PDF (`Ctrl+P` → Save as PDF).
4. **Zero Cloud Dependency:** The report is generated 100% locally and contains zero external CDN scripts, ensuring proprietary designs remain secure and air-gapped.

### 4.2 CSV Inventory & Findings Export
1. Click **Export CSV**.
2. PCB Insight generates two structured CSV files:
   - `components.csv`: Full Bill of Materials (BOM) inventory table.
   - `findings.csv`: Complete log of detected engineering findings with Rule IDs, explanations, and suggested corrective actions.

---

## 5. Troubleshooting & FAQ

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| **"Failed to connect to KiCad API server"** | KiCad API Server is disabled or blocked. | Go to KiCad **Preferences → Plugins → Enable API Server**. If using standalone CLI, specify the board file path directly. |
| **"kicad-cli not found"** | KiCad command-line tools are not on system PATH. | PCB Insight will automatically query KiCad for its installation directory over IPC. If running standalone, add `C:\Program Files\KiCad\9.0\bin` to your system PATH. |
| **"Unconnected pads reported on mounting holes"** | Mechanical holes (NPTH) have no electrical net. | This is normal behavior. Check the severity: NPTH pads are classified as **Information**, not Errors. |
