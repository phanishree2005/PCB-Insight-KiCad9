# Technical Boundaries & Limitations
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Document ID:** LIM-001  

---

## 1. Overview

In compliance with academic and professional engineering standards, PCB Insight maintains complete transparency regarding its operational scope, technical boundaries, and API limitations. This document records the architectural constraints identified during the feasibility and design phases.

---

## 2. KiCad 9 API Constraints

### 2.1 IPC API Version Maturity (KiCad 9 vs. KiCad 10)
- **KiCad 9.0 IPC API Baseline:** KiCad 9 introduced the Protocol Buffers / Nanomsg-NG IPC API. While core primitives (`get_footprints()`, `get_pads()`, `get_tracks()`, `get_vias()`, `get_nets()`, `get_shapes()`) are functional, advanced graph traversal methods such as `Board.get_connected_items()`, `Board.get_items_by_net()`, and reverse parent pointers (`Pad.parent`) were formally added in subsequent revisions (KiCad 10.0+ / `kicad-python` 0.7.0+).
- **PCB Insight Mitigation:** PCB Insight does not depend on nonexistent KiCad 9 IPC methods. Instead, it constructs the pad-to-net connectivity graph and component-pad relationships directly by traversing `FootprintInstance.definition.items` and querying `pad.net.name` and `pad.net.code`.

### 2.2 Live In-Memory Modifications vs. Disk State
- **Out-of-Process IPC Mode:** Reflects the active, open board state currently held inside the running KiCad PCB Editor memory.
- **Offline File Mode:** Reads the serialized `.kicad_pcb` file on disk. If a user makes edits in KiCad's GUI but has not saved (`Ctrl+S`), the offline parser reflects the last saved disk state. The user interface explicitly prompts the user to save changes prior to offline analysis.

---

## 3. Scope Boundaries: Custom Checks vs. Native DRC

| Domain | Handled by PCB Insight | Handled by KiCad Native DRC |
| :--- | :---: | :---: |
| **Component Reference Auditing** | **Yes** (Duplicates, missing, placeholders) | No |
| **BOM Value Hygiene** | **Yes** (Empty, default `~`, unassigned) | No |
| **Footprint Assignment Integrity** | **Yes** (Missing, malformed libraries) | Partial |
| **Single-Pin Net Detection** | **Yes** (Antenna / stub risk flagging) | Partial (Unconnected ratsnest) |
| **Floating Pad Classification** | **Yes** (Distinguishes NPTH vs SMD/PTH) | No |
| **BOM & Inventory Export** | **Yes** (Interactive HTML & CSV) | No |
| **Complex Physical Clearances** | No (Delegated to `kicad-cli`) | **Yes** (Micrometer geometric solver) |
| **Differential Pair Length Tuning** | No (EDA physical layout domain) | **Yes** |
| **Annular Ring Tolerances** | No (Fabrication CAM domain) | **Yes** |

PCB Insight does not attempt to reimplement complex 2D spatial polygon collision algorithms for copper trace clearances. Instead, when `kicad-cli` is detected on PATH, PCB Insight invokes `kicad-cli pcb drc --format json`, captures the authoritative DRC results, and embeds them into the unified engineering report.

---

## 4. Electrical and Simulation Boundaries
- **No 3D Full-Wave EM Simulation:** PCB Insight is a static design analyzer, not a finite-element 3D electromagnetic simulator (such as Ansys HFSS or open-source OpenEMS). It detects topological antenna risks (single-pin nets) but does not calculate S-parameters or radiation patterns.
- **No Circuit SPICE Simulation:** PCB Insight audits PCB layouts, not schematic electrical behavior. For analog transient or frequency-domain simulations, users should use eSim / ngspice directly.
- **Read-Only Invariant:** PCB Insight strictly does not modify, auto-route, or mutate board geometry without explicit user instruction. It is an auditing and reporting utility.
