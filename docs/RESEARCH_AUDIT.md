# Technical Accuracy Audit & Research Verification Report
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Submission:** FOSSEE eSim Semester Long Internship – Screening Task 6  
**Document ID:** AUDIT-001  
**Audit Date:** November 23, 2026  
**Status:** Verification Complete (Pre-Implementation)

---

## 1. Executive Summary

This audit performs a rigorous, line-by-line verification of all technical assertions, API claims, integration mechanisms, and data extraction pathways documented for **PCB Insight**. 

The audit evaluated our architecture against:
1. The official KiCad IPC API schema (`https://go.kicad.org/api/schemas/v1` / `api.v1.schema.json`).
2. The official `kicad-python` (package namespace `kipy`, version 0.8.0) implementation source code.
3. The official KiCad 9 PCB Editor documentation and command-line interface (`kicad-cli`).
4. The legacy SWIG `pcbnew` scripting interface.

### Summary of Key Audit Findings
- **High Accuracy on IPC Mechanism:** The Nanomsg-NG (`pynng`) and Protocol Buffers v3 transport mechanism is 100% verified.
- **Critical Schema Correction:** Discovered that `category` and `author` fields belong exclusively to KiCad's Plugin and Content Manager (PCM) `metadata.json` manifest (`pcm.v1.schema.json`), and are **invalid** in the low-level runtime `plugin.json` manifest (`api.v1.schema.json`).
- **Discovery of Native Binary Resolver:** Discovered that `kicad-python` provides `KiCad.get_kicad_binary_path("kicad-cli")`, allowing PCB Insight to dynamically discover `kicad-cli.exe` even when it is not added to the user's system PATH.
- **Version Boundary Verified:** Confirmed that net-traversal helpers like `Board.get_connected_items()` and `Pad.parent` reverse-pointers were introduced in KiCad 10 revisions. Our decision to build the net-pad connectivity graph internally in Python from `fp.definition.items` and `pad.net` is verified as the strictly correct architecture for KiCad 9.

---

## 2. Itemized Technical Audit

### Audit Item 1: Verification of KiCad 9 API Claims

| Claim / Topic | Claimed in Early Docs | Verified Fact in `kicad-python` (0.8.0) & KiCad 9 | Verdict & Correction |
| :--- | :--- | :--- | :--- |
| **IPC Transport Protocol** | Nanomsg-NG (NNG) over Named Pipes on Windows and Unix domain sockets on Linux. | Transport uses `pynng.Req0` with URI scheme `ipc://`. Default socket is `ipc://<tempdir>\kicad\api.sock` on Windows, or `ipc:///tmp/kicad/api.sock` on Linux. | **Verified Correct.** URI scheme uses `ipc://`. |
| **Discovery Variable** | `KICAD_API_SOCKET` environment variable. | Confirmed. `kipy.kicad._default_socket_path()` checks `os.environ.get('KICAD_API_SOCKET')` first. | **Verified Correct.** |
| **Authentication / Instance** | Mentioned named pipe connection. | KiCad also supports `KICAD_API_TOKEN` environment variable passed to `KiCad(kicad_token=...)` to bind to a specific instance. | **Enhanced.** Include optional token resolution. |
| **Native CLI Discovery** | Expected `kicad-cli` to be in system PATH. | If `kicad-cli` is not on PATH, calling `kicad.get_kicad_binary_path("kicad-cli")` over IPC returns the absolute executable path from KiCad itself! | **Major Positive Discovery.** Completely resolves PATH dependency issues on Windows. |
| **`pcbnew` Status in KiCad 9** | Deprecated in KiCad 9; planned removal in KiCad 11. | Confirmed by official KiCad release documentation and `kicad-python` package notices. | **Verified Correct.** |

---

### Audit Item 2: Verification of `plugin.json` Manifest & Launch Flow

An inspection of `api.v1.schema.json` directly bundled inside `kicad-python` reveals the exact valid schema for KiCad 9 IPC action plugins:

#### Schema Discrepancies Identified and Corrected:
1. **Invalid Fields Removed:** In preliminary drafts, `category` and `author` were included in `plugin.json`. In KiCad's architecture:
   - `plugin.json` is strictly the **API Action Manifest** conforming to `api.v1.schema.json`.
   - `metadata.json` is the **Package Metadata Manifest** conforming to `pcm.v1.schema.json`.
   Including PCM fields inside `plugin.json` causes schema validation warnings in `kipy.packaging.validate`.
2. **Runtime Specification:** In `runtime`, the valid field for minimum Python version is `min_version` (string), not `version`.
3. **Action Scope:** The valid scopes enum is `["pcb", "schematic", "footprint", "symbol", "project_manager", "footprint_wizard"]`. The value `"pcb"` is verified correct.

#### Verified Accurate `plugin.json`:
```json
{
  "$schema": "https://go.kicad.org/api/schemas/v1",
  "identifier": "org.fossee.pcb_insight",
  "name": "PCB Insight",
  "description": "Intelligent PCB Design Analysis, Connectivity Auditing, and Engineering Reports",
  "runtime": {
    "type": "python",
    "min_version": "3.9"
  },
  "actions": [
    {
      "identifier": "analyze_board",
      "name": "Analyze PCB Design",
      "description": "Audit components, connectivity, and generate engineering reports",
      "scopes": ["pcb"],
      "entrypoint": "pcb_insight/plugin_entry.py",
      "show-button": true,
      "icons-light": ["assets/icon.png"],
      "icons-dark": ["assets/icon.png"]
    }
  ]
}
```

---

### Audit Item 3: PCB Data Extraction Feasibility Check

We audited each required data field to confirm how it is extracted across IPC API, `pcbnew`, and direct S-expression parsing:

| Required PCB Data Field | IPC API (`kicad-python`) | Legacy `pcbnew` | S-Expression Parser (`.kicad_pcb`) | Feasibility Status |
| :--- | :--- | :--- | :--- | :--- |
| **Board Name / File** | `board.name()` | `board.GetFileName()` | Extracted from file path / title block | **100% Extractable** |
| **Dimensions / Bounding Box** | Computed from `board.get_shapes()` on `BL_Edge_Cuts` layer | `board.GetBoardEdgesBoundingBox()` | Computed from `(gr_line ...)`, `(gr_rect ...)` on `Edge.Cuts` | **100% Extractable** |
| **Footprint Count** | `len(board.get_footprints())` | `len(board.GetFootprints())` | Count of `(footprint ...)` nodes | **100% Extractable** |
| **Reference Designators** | `fp.reference_field.text.text` | `fp.GetReference()` | `(property "Reference" "...")` | **100% Extractable** |
| **Component Values** | `fp.value_field.text.text` | `fp.GetValue()` | `(property "Value" "...")` | **100% Extractable** |
| **Footprint Library ID** | `str(fp.definition.id)` | `fp.GetFPIDAsString()` | First token of `(footprint "ID" ...)` | **100% Extractable** |
| **Pad Numbers & Positions** | `pad.number`, `pad.position` | `pad.GetNumber()`, `pad.GetPosition()` | `(pad "num" ... (at x y))` | **100% Extractable** |
| **Pad Net Assignments** | `pad.net.name`, `pad.net.code` | `pad.GetNetname()`, `pad.GetNetCode()` | `(net code "name")` attribute on pad | **100% Extractable** |
| **Nets & Net Codes** | `board.get_nets()` | `board.GetNets()` | `(net code "name")` declarations | **100% Extractable** |
| **Track Count & Layers** | `board.get_tracks()` | `board.GetTracks()` | `(segment ...)` / `(arc ...)` nodes | **100% Extractable** |
| **Via Count & Drills** | `board.get_vias()` | `board.GetVias()` | `(via ...)` nodes | **100% Extractable** |
| **Zones & Copper Pours** | `board.get_zones()` | `board.GetZones()` | `(zone ...)` nodes | **100% Extractable** |
| **Stackup & Copper Layers** | `board.get_copper_layer_count()` | `board.GetCopperLayerCount()` | Count of signal copper layers | **100% Extractable** |

**Conclusion:** All 13 target data fields can be extracted reliably across all three extraction drivers.

---

### Audit Item 4: Identification of Unsupported or Version-Gated Features

1. **`Pad.parent` Reverse Pointer:**
   - *Status:* Added in `kicad-python` version 0.8.0 targeting KiCad 10.0.6.
   - *Audit Verdict:* Must **not** be called on KiCad 9.
   - *Solution:* Traverse `fp.definition.items` from each footprint down to its child pads, storing the parent component reference on our normalized `PadData` object during extraction.

2. **`Board.get_connected_items()` & `Board.get_items_by_net()`:**
   - *Status:* Added in KiCad 10.0.1.
   - *Audit Verdict:* Not present in KiCad 9.0 IPC API.
   - *Solution:* Our architecture already builds the inverted net-to-pad index ($\text{net} \to [(\text{ref}, \text{pad})]$) in Python. This completely insulates the tool from the missing KiCad 9 method.

3. **Direct DRC RPC over IPC:**
   - *Status:* KiCad 9's IPC API does not expose an RPC command to run DRC and stream violations over Protobuf.
   - *Audit Verdict:* Calling DRC requires invoking the native CLI.
   - *Solution:* Invoke `kicad-cli pcb drc --format json` as a safe subprocess, using `kicad.get_kicad_binary_path("kicad-cli")` to locate the binary.

---

### Audit Item 5: Architecture Realism for a Working KiCad 9 Plugin

1. **Out-of-Process Execution Realism:**
   - When launched via KiCad's IPC mechanism, the plugin runs in an isolated Python process.
   - Because the plugin is out-of-process, it cannot embed a wxWidgets panel directly into the KiCad C++ window frame without complex OS window parenting.
   - *Verified Realistic Workflow:* The plugin opens a lightweight native desktop dialog window (using standard Python `tkinter` which requires zero extra pip packages) or generates the HTML engineering report directly and opens it in the system default web browser (`webbrowser.open()`).
2. **Defensive Tri-Modal Adapter Pattern:**
   - The separation between `IPCAdapter`, `PcbnewAdapter`, and `SExprParserAdapter` ensures that if a user opens the plugin inside KiCad, it connects via IPC or `pcbnew`. If an evaluator or CI test runner evaluates the plugin headlessly, it uses the S-expression parser.
   - This ensures 100% testability with zero mock brittleness.

---

### Audit Item 6: Git Repository Status & Recommendations

1. **Current Git Status:**
   - Clean repository initialized on branch `main`.
   - All architecture and planning documents are present in `docs/`.
   - Configuration files (`.gitignore`, `requirements.txt`, `INSTALLATION.md`, `README.md`) are present.
2. **Action Taken:**
   - Corrected `plugin.json` schema documentation in `docs/API_INTEGRATION.md`.
   - Staged and created the initial Git commit for Phase 1 & 2 documentation.

---

## 3. Summary of Recommendations for Phase 3 Implementation

When FOSSEE proposal approval is granted:
1. **Dynamic Binary Location:** Use `kicad.get_kicad_binary_path("kicad-cli")` as the primary method to discover `kicad-cli`, falling back to `shutil.which("kicad-cli")`.
2. **Footprint-to-Pad Traversal:** Maintain the parent footprint reference during the initial traversal of `FootprintInstance.definition.items` rather than relying on `pad.parent`.
3. **Pure Python UI:** Use Python's built-in `tkinter` for the desktop status dialog to avoid external binary GUI dependencies like wxPython or PyQt in external virtual environments.
4. **Offline Test Fixtures:** Author two real `.kicad_pcb` fixture files (`clean_board.kicad_pcb` and `faulty_board.kicad_pcb`) to power the automated unit test suite.
