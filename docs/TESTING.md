# Verification, Validation & Testing Strategy
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Submission:** FOSSEE eSim Semester Long Internship – Screening Task 6  
**Document ID:** TEST-001  

---

## 1. Quality Assurance Philosophy

PCB Insight adheres to strict engineering verification principles:
1. **Zero Fabricated Evidence:** Tests must execute against real or accurately constructed PCB files. No mocked or simulated test runs will be presented as genuine live tests.
2. **Defensive Isolation:** Unit tests must be 100% executable headlessly without requiring a running KiCad desktop application or GUI session.
3. **Seeded Test Fixtures:** Validation uses two curated, standardized `.kicad_pcb` fixtures:
   - `clean_board.kicad_pcb`: A properly designed reference board with 0 critical errors.
   - `faulty_board.kicad_pcb`: A board intentionally seeded with specific, known design flaws to verify rule detection sensitivity.

---

## 2. Test Execution Matrix

| Test Suite | Target Module | Scope & Objectives | Execution Mechanism |
| :--- | :--- | :--- | :--- |
| **UT-01** | `pcb_insight.core.data_models` | Verify immutability, type hints, coordinate conversions, and defaults | `pytest tests/test_data_validation.py` |
| **UT-02** | `pcb_insight.integration.sexpr_parser` | Verify recursive S-expression tokenizer on valid and malformed KiCad files | `pytest tests/test_sexpr_parser.py` |
| **UT-03** | `pcb_insight.core.component_analyzer` | Verify prefix grouping (R, C, U), missing values, placeholder designators | `pytest tests/test_component_analyzer.py` |
| **UT-04** | `pcb_insight.core.connectivity_analyzer` | Verify net-pad graph, single-pin nets, floating pads, NPTH differentiation | `pytest tests/test_connectivity_analyzer.py` |
| **UT-05** | `pcb_insight.rules.rule_engine` | Verify rule registry, severity classification, finding aggregation | `pytest tests/test_rule_engine.py` |
| **UT-06** | `pcb_insight.reporting.html_report` | Verify standalone HTML synthesis, CSS inlining, table rendering | `pytest tests/test_report_generator.py` |
| **UT-07** | `pcb_insight.reporting.csv_exporter` | Verify RFC 4180 CSV export of components and findings | `pytest tests/test_report_generator.py` |
| **IT-01** | `pcb_insight.integration.ipc_adapter` | Verify live IPC socket connection and KiCad 9 RPC calls | KiCad 9 Live Session |
| **IT-02** | `pcb_insight.integration.drc_runner` | Verify safe execution of `kicad-cli pcb drc --format json` | CLI Subprocess Test |
| **E2E-01**| Full Pipeline (Clean Board) | End-to-end verification of clean board yielding zero errors | Headless CLI / KiCad |
| **E2E-02**| Full Pipeline (Faulty Board)| End-to-end verification of faulty board identifying all seeded defects | Headless CLI / KiCad |

---

## 3. Test Fixture Specifications

### 3.1 Fixture 1: `clean_board.kicad_pcb`
A valid 2-layer buck converter / 555 timer circuit:
- **Components:** 8 components properly annotated (`R1`, `R2`, `C1`, `C2`, `D1`, `U1`, `J1`, `TP1`).
- **Values:** Valid engineering values (`10k`, `100nF`, `1N4148`, `NE555P`, `Power_In`).
- **Footprints:** Standard KiCad library footprints assigned to all parts.
- **Nets:** Complete nets (`GND`, `+5V`, `Net-(R1-Pad1)`, `OUT`). Every net has $\ge 2$ pins except `TP1` (explicit test point).
- **Outline:** Closed rectangular boundary on `Edge.Cuts` (50.0 mm $\times$ 40.0 mm).
- **Tracks & Vias:** Fully routed copper traces on `F.Cu` and `B.Cu`.
- **Expected Outcome:** 0 Errors, 0 Warnings, Informational notice regarding test points.

### 3.2 Fixture 2: `faulty_board.kicad_pcb`
A board intentionally injected with classic hardware engineering oversights:
1. **Missing Reference:** A resistor with reference `"R?"` (`RULE-COMP-001`).
2. **Duplicate Reference:** Two distinct capacitors both labeled `"C1"` (`RULE-COMP-002`).
3. **Missing Value:** A diode with value `"~"` (`RULE-COMP-003`).
4. **Missing Footprint:** An IC with empty footprint string `""` (`RULE-COMP-004`).
5. **Single-Pin Net:** A net `"DANG_NET"` assigned only to `R1` pin 2 (`RULE-CONN-001`).
6. **Unassigned Pad:** Active IC pin on `U1` with empty net code (`RULE-CONN-003`).
7. **Missing Outline:** `Edge.Cuts` layer left empty with zero geometric shapes (`RULE-GEOM-001`).
8. **Expected Outcome:** Exactly 4 Errors, 3 Warnings, with accurate component designator evidence reported.

---

## 4. Live KiCad 9 Integration Verification Procedure

When testing inside a live KiCad 9 desktop environment:
1. Launch KiCad 9.
2. Enable the API Server:
   - Navigate to **Preferences > Plugins**.
   - Check **Enable API Server**.
   - Note socket or named pipe address.
3. Open KiCad PCB Editor.
4. Load sample board: `File > Open > tests/fixtures/clean_board.kicad_pcb`.
5. Trigger PCB Insight:
   - **Via IPC Manifest:** Click the PCB Insight icon in the top toolbar or run `python pcb_insight/plugin_entry.py`.
   - **Via Action Plugin:** Select **Tools > External Plugins > PCB Insight**.
6. The plugin window appears, displaying:
   - Board name and dimensions.
   - Component count and net count.
   - Findings summary card.
7. Click **Generate HTML Report**:
   - The standalone report is written to `output/report.html` and automatically displayed in the default web browser.
8. Click **Export CSV**:
   - Component inventory and findings tables are exported to `output/components.csv` and `output/findings.csv`.
