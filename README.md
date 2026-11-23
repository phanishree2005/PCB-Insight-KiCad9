# PCB INSIGHT 🔍⚡
### Intelligent PCB Design Analysis, Connectivity Auditing, and Engineering Report Generation for KiCad 9

[![KiCad 9 Compatible](https://img.shields.io/badge/KiCad-9.0+-blue.svg)](https://kicad.org)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-green.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FOSSEE Screening Task 6](https://img.shields.io/badge/FOSSEE-Screening%20Task%206-orange.svg)](docs/FOSSEE_SUBMISSION_CHECKLIST.md)

---

## 📌 Executive Overview
**PCB Insight** is an intelligent, modular, and explainable PCB design analysis utility designed specifically for **KiCad 9**. It bridges Computer Science (modular software design, rule engines, graph models, typed dataclasses) with Electronics Design Automation (pad-to-net topology, Bill of Materials hygiene, footprint validation, and Design for Manufacturing checks).

Developed for the **FOSSEE eSim Semester Long Internship – Autumn 2026 (Screening Task 6)**, PCB Insight inspects printed circuit board designs, identifies subtle electrical and metadata anomalies, and synthesizes standalone, interactive engineering reports.

---

## 🚀 Key Features

| Capability | Engineering Focus | Technical Description |
| :--- | :--- | :--- |
| **KiCad 9 IPC Integration** | Modern Out-of-Process Architecture | Directly connects to KiCad 9's official IPC API (`kicad-python`) via Protocol Buffers and Nanomsg-NG named pipes / sockets. |
| **Legacy pcbnew Fallback** | Maximum Compatibility | Seamless fallback to in-process `pcbnew.ActionPlugin` for classic toolbar execution in existing KiCad installations. |
| **Component Health Audit** | Bill of Materials (BOM) Hygiene | Evaluates component references against IEEE Std 315/200; detects duplicates, missing values (`~`), placeholder designators (`R?`), and unassigned footprints. |
| **Connectivity Graph Engine** | Electrical Sanity & Antenna Detection | Builds a complete net-to-pad topological index; detects dangling single-pin nets (RF stubs), unassigned active pads, and differentiates mechanical mounting holes (NPTH). |
| **Explainable Rule Engine** | Deterministic Quality Verification | Modular rule architecture where every reported finding includes a unique Rule ID, severity classification, affected components/nets, technical rationale, and remediation steps. |
| **Native KiCad DRC Traceability**| Authoritative Validation | Safely invokes `kicad-cli pcb drc --format json` when available to incorporate native DRC violations without duplicating clearance solvers. |
| **Air-Gapped HTML & CSV Reports**| Zero-Network Data Security | Generates single-file, responsive, print-friendly HTML reports with search/filtering, plus RFC 4180 CSV exports of component inventories and findings. |
| **Offline S-Expression Engine** | Headless Testing & CI/CD | Pure-Python recursive S-expression parser for `.kicad_pcb` files allowing 100% headless testing without requiring a live KiCad GUI session. |

---

## 🏗 System Architecture

PCB Insight follows a **Hexagonal (Ports-and-Adapters) Clean Architecture**:

```
+-----------------------------------------------------------+
|                   External KiCad Sources                  |
|  [KiCad 9 IPC API]   [Legacy pcbnew]   [.kicad_pcb File]  |
+-----------------------------------------------------------+
                              |
                   [BoardAdapter Interface]
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
| - Component Analyzer  |               | - Standalone HTML |
| - Net Connectivity    |               | - CSV Exporter    |
| - Design Quality Rules|               | - Summary Cards   |
+-----------------------+               +-------------------+
```

Full details are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md).

---

## 📚 Technical Documentation Suite

The repository contains comprehensive engineering documentation:
- 📖 **[Design Document (27 Sections)](docs/DESIGN_DOCUMENT.md):** Complete technical specifications, algorithms, diagrams, and methodologies.
- 🏛 **[System Architecture](docs/ARCHITECTURE.md):** Architectural patterns, data models, and sequence flows.
- ⚖️ **[Technical Decisions (ADRs)](docs/TECHNICAL_DECISIONS.md):** Justification for IPC API selection, fallbacks, and design trade-offs.
- 🔌 **[API Integration Guide](docs/API_INTEGRATION.md):** Deep comparison of KiCad 9 IPC API vs. legacy `pcbnew` SWIG bindings.
- ⚡ **[Electronics Concepts](docs/ELECTRONICS_CONCEPTS.md):** Reference designators, pad types, net topology, and RF stub physics.
- 🧪 **[Testing Strategy](docs/TESTING.md):** Test execution matrix, clean and faulty fixture specifications.
- ⚠️ **[Technical Limitations](docs/LIMITATIONS.md):** Documented boundaries and operational scope.
- ✅ **[FOSSEE Submission Checklist](docs/FOSSEE_SUBMISSION_CHECKLIST.md):** Direct mapping of internship criteria to implementation modules.

---

## 💻 Installation & Quick Start

Refer to [INSTALLATION.md](INSTALLATION.md) for complete multi-platform setup instructions.

```bash
# 1. Clone repository
git clone https://github.com/username/PCB-Insight-KiCad9-Plugin.git
cd PCB-Insight-KiCad9-Plugin

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated test suite
pytest tests/ -v
```

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
