# Technical Decisions & Architecture Selection
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Submission:** FOSSEE eSim Semester Long Internship – Screening Task 6  
**Document ID:** TD-001  
**Status:** Approved for Planning Phase  

---

## 1. Architectural Decision Record (ADR) Overview

| ADR ID | Decision Title | Status | Primary Driver |
| :--- | :--- | :--- | :--- |
| **ADR-01** | Modern IPC API as Primary Integration Driver | **Accepted** | KiCad 9 deprecation of SWIG bindings; future-proof design |
| **ADR-02** | Legacy `pcbnew.ActionPlugin` as Documented Fallback | **Accepted** | Seamless in-editor execution for existing KiCad installations |
| **ADR-03** | Standalone S-Expression Parser for Offline & Testability | **Accepted** | Headless testing, CI/CD verification without running KiCad GUI |
| **ADR-04** | Normalized Data Models (Hexagonal / Port-and-Adapter) | **Accepted** | Decouple analysis engines from external KiCad C++/Protobuf types |
| **ADR-05** | KiCad Native DRC Delegation via `kicad-cli` | **Accepted** | Avoid reinventing DRC geometry algorithms; trace authoritative results |
| **ADR-06** | Pure Python Standalone HTML/CSS/JS Offline Reporting | **Accepted** | Zero external CDN dependency; air-gapped engineering security |

---

## 2. ADR-01: Primary Integration via KiCad 9 IPC API (`kicad-python`)

### Context
Historically, KiCad plugin development relied on SWIG C++ wrapper bindings (`import pcbnew`). With the release of KiCad 9, the KiCad development team introduced a redesigned Inter-Process Communication (IPC) architecture and declared the legacy SWIG bindings **deprecated**, with planned complete removal in KiCad 11.

### Decision
PCB Insight adopts KiCad 9's official **IPC API** as the primary integration architecture:
1. The plugin provides a modern manifest (`plugin.json`) conforming to the KiCad 9 schema (`https://go.kicad.org/api/schemas/v1`).
2. KiCad launches PCB Insight as an independent, out-of-process Python application.
3. PCB Insight uses `kicad-python` (`kipy`) to establish a client connection over the IPC transport (Named Pipe on Windows, Unix domain socket on POSIX) discovered via the `KICAD_API_SOCKET` environment variable.
4. Board elements (footprints, pads, tracks, vias, zones, stackup) are queried via strongly-typed Protocol Buffer RPC messages.

### Rationale
- **Stability:** A defect or crash in the plugin does not bring down the PCB Editor or risk corrupting open unsaved designs.
- **Dependency Isolation:** Out-of-process execution prevents library version conflicts (e.g., protobuf, pynng, or Python minor version mismatches) with KiCad's bundled interpreter.
- **Academic & Industry Relevance:** FOSSEE evaluators value forward-looking, production-grade engineering over obsolete legacy techniques.

---

## 3. ADR-02: Legacy `pcbnew.ActionPlugin` as Documented Fallback

### Context
While the IPC API is the future of KiCad, many users and academic lab workstations run standard KiCad 9 with default settings where the IPC API Server (`Preferences > Plugins > Enable API Server`) may not yet be enabled, or where users prefer invoking plugins directly from the PCB Editor toolbar menu via classic `.py` Action Plugins placed in `kicad/scripting/plugins`.

### Decision
PCB Insight provides a fully compatible **`pcbnew.ActionPlugin` fallback bridge** (`pcb_insight/integration/kicad_adapter.py`):
1. An Action Plugin entrypoint (`PCBInsightActionPlugin`) registers in the KiCad PCB Editor menu: `Tools > External Plugins > PCB Insight`.
2. When triggered, it checks if `pcbnew` is available in the current Python environment.
3. If available, it extracts the in-memory `pcbnew.BOARD` object and normalizes it into our internal `BoardData` structure before passing it to the core analysis engine.

### Rationale
Ensures 100% usability across both cutting-edge IPC setups and standard desktop KiCad 9 installations without requiring command-line configuration from non-technical users.

---

## 4. ADR-03: Standalone S-Expression Parser for Headless Testing

### Context
Unit testing and automated grading require evaluating the plugin against multiple board fixtures (clean boards, boards with missing references, boards with unassigned nets, boards with missing outlines) in environments where the interactive KiCad GUI cannot be launched (such as GitHub Actions or headless grading scripts).

### Decision
PCB Insight implements a lightweight, pure-Python S-expression parser (`pcb_insight/integration/sexpr_parser.py`) capable of reading `.kicad_pcb` files directly into the same normalized `BoardData` model.

### Rationale
- Enables fast, headless unit tests (`pytest`) executing in milliseconds.
- Enables CLI execution (`python -m pcb_insight path/to/board.kicad_pcb`).
- Eliminates brittle mocks while keeping integration tests authentic.

---

## 5. ADR-04: Normalized Data Model Architecture (Port and Adapter Pattern)

### Context
Directly passing raw `pcbnew.FOOTPRINT` or `kipy.board_types.FootprintInstance` objects across the analysis and rule engines creates tight coupling, makes testing difficult, and causes fragile code when KiCad minor versions alter underlying protobuf or C++ fields.

### Decision
All raw external representations are immediately converted into immutable or typed Python dataclasses:
- `BoardData`
- `ComponentData`
- `FootprintData`
- `PadData`
- `NetData`
- `TrackData`
- `ViaData`
- `ZoneData`
- `AnalysisFinding`
- `AnalysisResult`

Every analysis engine, rule engine, and report exporter operates **exclusively** on these internal models.

```
+-----------------------------------------------------------+
|                   External KiCad Sources                  |
|  [KiCad 9 IPC API]   [Legacy pcbnew]   [.kicad_pcb File]  |
+-----------------------------------------------------------+
                              |
                     [Adapter Interface]
                              v
+-----------------------------------------------------------+
|               Normalized Data Models (Core)               |
|      BoardData, ComponentData, NetData, PadData, etc.     |
+-----------------------------------------------------------+
                              |
          +-------------------+-------------------+
          v                                       v
+-----------------------+               +-------------------+
|  Analysis & Rules     |               | Reporting Engine  |
| - Component Analyzer  |               | - HTML Exporter   |
| - Net Connectivity    |               | - CSV Exporter    |
| - Design Quality Rules|               | - Summary Cards   |
+-----------------------+               +-------------------+
```

---

## 6. ADR-05: Native KiCad DRC Delegation via `kicad-cli`

### Context
A common mistake in student PCB analyzer projects is writing naive geometry collision checkers and claiming to replace KiCad's Design Rules Checker (DRC). KiCad's native DRC has decades of engineering handling complex clearance rules, zone fills, net classes, differential pairs, and annular rings.

### Decision
PCB Insight strictly delineates:
1. **PCB Insight Custom Checks:** Focuses on higher-level electronics design quality, component metadata integrity, net connectivity health, Bill of Materials (BOM) readiness, and layout sanity.
2. **KiCad Native DRC:** When `kicad-cli` is present, PCB Insight runs `kicad-cli pcb drc --format json` as a subprocess, captures the authoritative native electrical and physical DRC violations, and presents them in a dedicated section of the engineering report with full traceability.
3. If `kicad-cli` is not installed, PCB Insight cleanly notes the limitation in the report while keeping all custom rules fully operational.

---

## 7. ADR-06: Self-Contained Offline HTML/CSS/JS Reporting

### Context
PCB designs in engineering, defense, and academic research are proprietary. Uploading designs to third-party cloud servers or relying on external CDN scripts (which fail in air-gapped lab computers) violates basic engineering ethics and security.

### Decision
1. All generated reports are single-file, responsive HTML documents with inline CSS and lightweight vanilla JS.
2. Zero external network calls or remote CDNs.
3. Print-friendly CSS (`@media print`) enables direct "Save as PDF" for engineering documentation.
4. CSV export for components and findings enables spreadsheet ingestion.
