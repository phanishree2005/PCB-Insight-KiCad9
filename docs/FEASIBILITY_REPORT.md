# Technical Feasibility & Environment Inspection Report
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Submission Context:** FOSSEE eSim Semester Long Internship – Autumn 2026 (Screening Task 6)  
**Date of Inspection:** November 23, 2026  
**Status:** Phase 1 Complete (Awaiting User Proposal Approval Before Implementation)

---

## 1. Executive Summary

This feasibility report documents the findings from inspecting the host development environment, evaluating KiCad 9 architectural integration mechanisms (IPC API vs. legacy SWIG bindings vs. standalone parser), and verifying Python package compatibility.

Our investigation confirms that:
1. **KiCad 9 has established an official Inter-Process Communication (IPC) API**, supported by the official client library `kicad-python` (version 0.8.0), communicating via Nanomsg-NG (`pynng`) and Protocol Buffers v3 (`protobuf`).
2. **The legacy SWIG-based Python bindings (`pcbnew`)** remain available in KiCad 9 and 10 but are officially deprecated as of KiCad 9 and slated for total removal in KiCad 11.
3. To achieve a modern, reliable, and testable engineering tool, **PCB Insight adopts a Dual-Adapter Architecture**:
   - **Primary Driver:** KiCad 9 IPC API via `kicad-python` using an out-of-process `plugin.json` manifest.
   - **Fallback Driver:** In-process KiCad `pcbnew.ActionPlugin` adapter for environments where the IPC API daemon is disabled.
   - **Offline / Headless Engine:** Native `.kicad_pcb` S-expression parser providing complete offline analysis, unit testing, and headless CLI capabilities without requiring a running KiCad GUI session.

---

## 2. Development Environment Inspection Matrix

| Parameter | Observed Host Value | Compatibility Assessment | Action / Mitigation |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise/Pro (Build 10.0.26300.0, 64-bit AMD64) | **Compatible** | Windows Named Pipe IPC transport supported by `pynng` |
| **Python Version** | Python 3.14.0 (`C:\Python314\python.exe`) | **Compatible** | Meets `kicad-python` requirement (`>=3.9`); modern type hinting supported |
| **Git Version** | git version 2.51.1.windows.1 | **Compatible** | Dedicated repository initialized in workspace |
| **Workspace Directory** | `C:\Users\Phanishree N\OneDrive\Pictures\Documents\Desktop\PCB-Insight-KiCad9` | **Compatible** | Isolated project root, clean branch `main` |
| **KiCad 9 Host Installation** | Not detected in default registry or `C:\Program Files\KiCad` | **Inspection Finding** | Host has `winget` and `choco` available. For developer workflow, standalone S-expression parser enables 100% test coverage; user can install KiCad 9 via `winget install KiCad.KiCad` or official installer. |
| **kicad-python Package** | Version 0.8.0 available on PyPI; binary wheels for Python 3.14 verified | **Fully Compatible** | Requires `protobuf<6,>=5.29`, `pynng<0.10.0,>=0.9.0`, `jsonschema<5,>=4.23.0` |
| **KiCad CLI (`kicad-cli`)** | Supported by KiCad 9 (`kicad-cli pcb drc --format json`) | **Evaluated** | Integration designed to execute safely when binary is present, with graceful degradation when absent |

---

## 3. KiCad 9 API Investigation

### 3.1 Official KiCad IPC API (`kicad-python` / `kipy`)

KiCad 9 represents the transition from embedded C++ bindings to decoupled out-of-process client-server IPC.

- **Transport:** Nanomsg-NG (NNG). On Windows, it operates over Named Pipes (`\\.\pipe\kicad-api-...`). On Linux and macOS, it operates over Unix Domain Sockets (`api.sock`).
- **Serialization:** Protocol Buffers v3 (`.proto` message definitions).
- **Client Discovery:** When KiCad launches an external plugin declared in `plugin.json`, it exposes the socket address through the `KICAD_API_SOCKET` environment variable.
- **Client Library:** `kicad-python` (package namespace `kipy`).

#### Supported Capabilities in KiCad 9 IPC API:
- `KiCad.get_board()`: Retrieves the active PCB layout.
- `Board.name()`: Board project identifier/filename.
- `Board.get_footprints()`: Returns list of `FootprintInstance` items.
  - Footprint reference: `fp.reference_field.text.text`
  - Footprint value: `fp.value_field.text.text`
  - Footprint definition: `fp.definition.id` (e.g. `Resistor_SMD:R_0805_2012Metric`)
  - Footprint position, layer, orientation, locked status.
  - Footprint child items: `fp.definition.items` containing child `Pad` objects.
- `Board.get_pads()`: Returns list of all pads across the board.
  - Pad number: `pad.number` (e.g. "1", "2")
  - Pad net: `pad.net.name` (e.g. "GND", "+3V3", "Net-(R1-Pad1)") and `pad.net.code`
  - Pad type: `PadType` (PTH, SMD, NPTH, etc.)
  - Pad coordinates: `pad.position`
- `Board.get_tracks()`: Returns list of `Track` and `ArcTrack` items with net assignment and layer.
- `Board.get_vias()`: Returns list of `Via` items with net assignment, drill size, and padstack.
- `Board.get_zones()`: Returns list of filled and unfilled copper zones with assigned nets.
- `Board.get_nets()`: Returns all defined nets on the board.
- `Board.get_shapes()`: Returns board geometry including `Edge.Cuts` boundary lines and polygons.
- `Board.get_stackup()` & `Board.get_copper_layer_count()`: Layer stackup and layer configurations.

#### Identified Limitations of KiCad 9 IPC API:
1. **Requires Active KiCad Session:** The IPC API requires a running KiCad instance with the API server enabled (`Preferences > Plugins > Enable API Server`). It cannot parse `.kicad_pcb` files from cold storage without KiCad running.
2. **Net Connectivity Graph:** In KiCad 9.0, advanced net connectivity queries like `Board.get_connected_items()` and `Pad.parent` reverse-pointers were introduced in KiCad 10 / 10.0.1+. In KiCad 9.0, pad-to-component mappings are extracted by traversing `FootprintInstance.definition.items`, and pad-to-net mapping is extracted from `Pad.net`.
3. **DRC Execution:** The IPC API does not provide a direct RPC to trigger the full native DRC solver. KiCad's authoritative DRC is invoked via `kicad-cli pcb drc --format json`.

### 3.2 Legacy SWIG Python Bindings (`pcbnew`)

- **Mechanism:** In-process C++ wrappers generated by SWIG, running inside KiCad's embedded Python interpreter.
- **Plugin Type:** `pcbnew.ActionPlugin`.
- **Status in KiCad 9:** **Deprecated**. KiCad documentation explicitly marks `pcbnew` as deprecated starting in KiCad 9 and scheduled for removal in KiCad 11.
- **Strengths:** Direct in-memory C++ pointers to `BOARD`, `FOOTPRINT`, `PAD`, `ZONE`, `NETINFO_ITEM`.
- **Weaknesses:** Embedded interpreter dependencies (must use KiCad's internal Python interpreter), crash risks (unhandled exceptions can terminate KiCad), cannot be executed in external CI/CD pipelines without KiCad's specific build environment.

### 3.3 Standalone `.kicad_pcb` S-Expression Parser

- **Mechanism:** KiCad board files (`.kicad_pcb`) use a standardized, human-readable S-expression grammar format (version 20240108 for KiCad 8/9).
- **Strengths:** 
  - 100% decoupled from KiCad GUI or running daemon.
  - Enables comprehensive automated testing, CI/CD regression suites, and headless CLI operation.
  - Extracts exact pad coordinates, footprints, nets, tracks, vias, zones, and board boundaries directly.
- **Weaknesses:** Does not dynamically reflect uncommitted in-memory edits before saving to disk.

---

## 4. Conclusion & Recommended Architecture

To comply with the prompt's mandate ("investigate the IPC API first, verify what KiCad 9 actually supports, and use a documented fallback only if necessary; it should not be hard coded"):

PCB Insight will be implemented with an **Adapter / Strategy Pattern**:
- An abstract `BoardAdapter` interface defines common contract methods (`extract_board_data() -> BoardData`).
- `IPCAdapter`: Modern out-of-process KiCad 9 driver talking to `kicad-python`.
- `PcbnewAdapter`: In-process KiCad 9 Action Plugin driver for legacy compatibility.
- `FileParserAdapter`: Pure Python S-expression parser for automated unit testing, sample fixtures, and headless CI runs.
- `NativeDRCAdapter`: Subprocess wrapper around `kicad-cli pcb drc --format json` to ingest authoritative KiCad DRC findings without duplicating DRC solver code.

All internal engines (Component Analysis, Connectivity Analysis, Rule Engine, Report Generator) operate exclusively on strongly-typed, normalized data models (`BoardData`, `ComponentData`, `NetData`, etc.), ensuring complete independence from any single API binding.

---

## 5. Proposal Approval Gate

As specified in the FOSSEE eSim task instructions and user directives:
- This document concludes **Phase 1 (Environment Feasibility)** and establishes the foundation for **Phase 2 (Architecture & Specification)**.
- **Implementation (Phase 3) remains gated** until explicit proposal approval is confirmed by the user.
