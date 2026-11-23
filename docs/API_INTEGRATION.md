# KiCad API Integration Guide: IPC API vs. pcbnew
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Document ID:** API-001  

---

## 1. Overview of KiCad 9 Integration Pathways

KiCad 9 represents a major inflection point in EDA scripting architectures. Hardware developers and plugin authors have two programmatic mechanisms available within the KiCad ecosystem, plus an offline S-expression file interface:

```
+---------------------------------------------------------------------------------+
|                               KiCad 9 Application                               |
|                                                                                 |
|  +------------------------+                        +-------------------------+  |
|  |     PCB Editor GUI     |                        |  IPC API Server Daemon  |  |
|  |                        |                        |  (Nanomsg-NG / Protobuf)|  |
|  +-----------+------------+                        +------------+------------+  |
|              |                                                  |               |
+--------------|--------------------------------------------------|---------------+
               | (In-Process C++ SWIG)                            | (Out-of-Process Socket)
               v                                                  v
   [pcbnew.ActionPlugin]                                  [kicad-python (kipy)]
   (Legacy / Deprecated)                                  (Modern KiCad 9 Standard)
               |                                                  |
               +----------------------+---------------------------+
                                      v
                        [PCB Insight BoardAdapter]
                                      ^
                                      | (Direct File Read)
                        [.kicad_pcb S-Expression]
```

---

## 2. Pathway 1: KiCad 9 IPC API (`kicad-python` / `kipy`)

### 2.1 Technical Mechanism
The KiCad 9 IPC API operates out-of-process. KiCad runs an internal API server daemon using Nanomsg-NG (`pynng`) for network framing and Google Protocol Buffers v3 (`protobuf`) for data serialization.

On Windows platforms, IPC transport operates over **Windows Named Pipes**:
`\\.\pipe\kicad-api-<token>`

On Linux and macOS platforms, IPC transport operates over **Unix Domain Sockets**:
`/tmp/kicad-api-<token>.sock` or `$XDG_RUNTIME_DIR/kicad/api.sock`

When KiCad triggers an external action plugin defined in `plugin.json`, it exports the active pipe/socket path in the environment variable:
`KICAD_API_SOCKET`

### 2.2 Modern Plugin Manifest (`plugin.json`)
The plugin directory is installed into KiCad's 3rd-party plugins directory (`%APPDATA%\kicad\9.0\plugins\` on Windows or `~/.local/share/kicad/9.0/plugins/` on Linux).

In KiCad 9's architecture, `plugin.json` is strictly the **API Action Manifest** conforming to `https://go.kicad.org/api/schemas/v1` (`api.v1.schema.json`). Note that package distribution metadata (such as `author` and `category`) belongs in the separate `metadata.json` manifest (`pcm.v1.schema.json`) for the Plugin and Content Manager (PCM).

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

### 2.3 Extraction Code Flow using `kicad-python`
```python
import os
import kipy
from kipy.kicad import KiCad
from pcb_insight.core.data_models import BoardData, ComponentData, PadData, NetData

def extract_from_ipc() -> BoardData:
    socket_path = os.environ.get("KICAD_API_SOCKET")
    kicad_client = KiCad(socket_path=socket_path)
    board = kicad_client.get_board()
    
    # Extract Footprints & Components
    components = []
    for fp in board.get_footprints():
        ref = fp.reference_field.text.text if fp.reference_field else ""
        val = fp.value_field.text.text if fp.value_field else ""
        fp_id = str(fp.definition.id) if fp.definition else ""
        pos = fp.position
        
        # Extract Child Pads
        pads = []
        for item in fp.definition.items:
            if hasattr(item, "number") and hasattr(item, "net"):
                pad_data = PadData(
                    pad_number=str(item.number),
                    net_name=item.net.name if item.net else "",
                    net_code=item.net.code if item.net else 0,
                    pad_type=str(item.pad_type),
                    position_x_mm=item.position.x / 1_000_000.0,
                    position_y_mm=item.position.y / 1_000_000.0,
                    size_x_mm=item.size.x / 1_000_000.0 if hasattr(item, "size") else 0.0,
                    size_y_mm=item.size.y / 1_000_000.0 if hasattr(item, "size") else 0.0,
                    layers=(str(item.layer),)
                )
                pads.append(pad_data)
                
        components.append(ComponentData(
            reference=ref,
            prefix=ref.rstrip("0123456789"),
            value=val,
            footprint_name=fp_id,
            layer=str(fp.layer),
            position_x_mm=pos.x / 1_000_000.0,
            position_y_mm=pos.y / 1_000_000.0,
            orientation_deg=fp.orientation.degrees if hasattr(fp.orientation, "degrees") else 0.0,
            pads=pads
        ))
        
    return BoardData(
        name=board.name(),
        file_path=None,
        dimensions_mm=(0.0, 0.0),
        bounding_box=(0.0, 0.0, 0.0, 0.0),
        copper_layer_count=board.get_copper_layer_count(),
        enabled_layers=[str(l) for l in board.get_enabled_layers()],
        components=components,
        nets={},
        track_count=len(board.get_tracks()),
        via_count=len(board.get_vias()),
        zone_count=len(board.get_zones())
    )
```

---

## 3. Pathway 2: Legacy SWIG Bindings (`pcbnew.ActionPlugin`)

### 3.1 Technical Mechanism
`pcbnew` is KiCad's legacy SWIG-generated C++ Python module. It runs directly inside KiCad's embedded Python interpreter. In KiCad 9, this interface is officially **deprecated** and will be eliminated in KiCad 11.

### 3.2 Action Plugin Implementation
An Action Plugin is placed in `%APPDATA%\kicad\9.0\scripting\plugins\` (Windows) or `~/.local/share/kicad/9.0/scripting/plugins/` (Linux).

```python
import pcbnew
from pcb_insight.core.data_models import BoardData, ComponentData, PadData

class PCBInsightActionPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "PCB Insight"
        self.category = "Design Analysis"
        self.description = "Audit PCB components, nets, and generate engineering reports"
        self.show_toolbar_button = True
        self.icon_file_name = ""

    def Run(self):
        board = pcbnew.GetBoard()
        # Extract board primitives and dispatch to PCB Insight Analysis Engine
        # ...
```

---

## 4. Pathway 3: Standalone S-Expression Parser (`.kicad_pcb`)

### 4.1 Technical Mechanism
KiCad PCB files use a recursive nested S-expression format:
```scheme
(kicad_pcb
  (version 20240108)
  (generator "kicad")
  (generator_version "9.0")
  (general
    (thickness 1.6)
  )
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (48 "Edge.Cuts" user)
  )
  (net 0 "")
  (net 1 "GND")
  (net 2 "+3V3")
  (footprint "Resistor_SMD:R_0805_2012Metric"
    (layer "F.Cu")
    (uuid "00000000-0000-0000-0000-000067300001")
    (at 120.5 85.0)
    (property "Reference" "R1" (at 120.5 83.5 0))
    (property "Value" "10k" (at 120.5 86.5 0))
    (pad "1" smd roundrect (at -0.95 0) (size 1.0 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (net 2 "+3V3"))
    (pad "2" smd roundrect (at 0.95 0) (size 1.0 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "GND"))
  )
)
```

The pure-Python recursive tokenizer parses nested parentheses into Python tree lists `[tag, *elements]`, enabling fast, complete extraction of:
- Footprints, references, values, layers, and positions
- Pads, pad numbers, net assignments, coordinates, and pad types
- Net declarations and net codes
- Tracks, arcs, and vias
- Filled zones and copper pour boundaries
- Graphic lines and arcs on `Edge.Cuts` for board outline dimensions

---

## 5. Summary Decision Matrix

| Dimension | KiCad 9 IPC API (`kicad-python`) | Legacy SWIG (`pcbnew`) | Direct S-Expression Parser |
| :--- | :--- | :--- | :--- |
| **KiCad 9 Status** | **Official Recommended** | **Deprecated** (Removed in v11) | Independent File Format |
| **Execution Model** | Out-of-Process (Safe) | In-Process (Can Crash KiCad) | Headless / Offline Process |
| **Requires KiCad Open?** | Yes | Yes | **No** |
| **Automated CI/CD Testing** | Difficult (Needs GUI Daemon) | Difficult (Needs KiCad Build) | **Seamless (`pytest`)** |
| **Interactive UX in Editor** | Yes (via `plugin.json` Action) | Yes (via Toolbar Menu) | CLI / Batch Tool |
| **PCB Insight Role** | **Primary Integration** | **Documented Fallback** | **Headless Testing Engine** |
