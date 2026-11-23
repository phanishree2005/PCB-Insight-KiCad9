# Electronics & PCB Engineering Principles in PCB Insight
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Submission:** FOSSEE eSim Semester Long Internship – Screening Task 6  
**Document ID:** ELEC-001  

---

## 1. Overview of Electronic Design Verification

Electronic Design Automation (EDA) bridges abstract mathematical circuit theory and physical electromagnetic hardware. A schematic diagram defines functional intent and net topology, while a Printed Circuit Board (PCB) realizes those connections as physical copper traces, dielectric substrate layers, plated holes, and surface mount footprints.

PCB Insight audits the physical layout to identify discrepancies between engineering intent, assembly requirements, and manufacturing tolerances.

---

## 2. Component Taxonomy & Reference Designators

### 2.1 Standard Reference Designators (IEEE Std 315-1975 / IEEE Std 200-1975)
In standard electronics documentation and Bill of Materials (BOM) management, components are categorized by alphabetical class prefixes followed by sequential integers:

| Prefix | Component Category | Electrical Purpose | Typical Audit Checks |
| :--- | :--- | :--- | :--- |
| **R** | Resistor | Current limiting, pull-up/down, voltage divider | Verify numeric nominal value, tolerance, package power rating |
| **C** | Capacitor | Decoupling, bypass, timing, DC blocking, filtering | Check capacitance value, dielectric rating, proximity to IC supply |
| **L** | Inductor / Ferrite Bead | Energy storage, EMI attenuation, RF filtering | DC resistance, saturation current, value |
| **D** | Diode / LED / TVS | Rectification, optical indication, ESD clamping | Polarity orientation, forward voltage, anode/cathode nets |
| **Q** | Transistor (BJT / FET) | Switching, analog amplification | Pinout mapping (G-D-S vs B-C-E), thermal dissipation |
| **U / IC** | Integrated Circuit | Processing, logic, analog computation | Power/ground pins connected, decoupling capacitors assigned |
| **J / P** | Connector / Header | External I/O, power injection, debugging | Pin 1 orientation, current carrying capacity, shroud clearance |
| **SW** | Switch / Pushbutton | User interface, state selection | Pull-up/pull-down net integrity, debounce compatibility |
| **TP** | Test Point | Production line automated test fixtures (ICT) | Net assignment, clearance for pogo pins, single-pin intent |
| **FID** | Fiducial Marker | Optical alignment for pick-and-place cameras | NPTH / copper pad without net assignment (expected) |
| **H / MH** | Mounting Hole | Chassis mechanical assembly, earth bonding | Earth ground vs isolated, clearance for screw heads |

### 2.2 BOM Hygiene & Metadata Quality
Hardware assembly lines rely on machine-readable Pick-and-Place (centroid) files and BOM spreadsheets. Common metadata failures detected by PCB Insight include:
- **Unassigned Designators:** Designators containing `"?"` (e.g. `R?`) or placeholder tags (`"REF**"`) signify unannotated schematics.
- **Duplicate Designators:** Two distinct physical parts bearing identical designators (`C1` and `C1`) cause centroid collisions and pick-and-place halts.
- **Empty or Placeholder Values:** Values recorded as `""`, `"~"`, or `"Value"` lead to purchasing ambiguities and incorrect assembly.
- **Missing Footprint Identifiers:** Components lacking physical footprint definitions cannot be fabricated or placed.

---

## 3. Electrical Nets & Connectivity Graph Topology

### 3.1 Net Definitions
An electrical net is an equipotential conductor connecting two or more component pads together. In KiCad:
- Nets are identified by unique string names (e.g., `+3V3`, `GND`, `Net-(R1-Pad1)`).
- Every net is indexed with an integer Net Code (Net 0 is conventionally reserved for unconnected / unassigned).

### 3.2 Single-Pin Net Anomalies (Antenna & Stub Risks)
A net associated with exactly **one** physical pad ($N_{\text{pads}} = 1$) is a critical warning condition:
1. **Accidental Net Labels:** In schematic capture, an engineer may place a net label (e.g. `RESET_L`) but forget to place the corresponding receiver label on the microcontroller pin.
2. **RF Antenna Effects:** An unrouted or dangling single-pin copper trace acts as an open-ended transmission line stub. At high frequencies, stubs act as quarter-wave resonant antennas that emit radiated electromagnetic interference (EMI) or collect ambient RF noise.
3. **Intentional Exceptions:** Genuine single-pin nets include designated Test Points (`TP1`) or isolated antenna radiator pads. PCB Insight intelligently distinguishes test points by component prefix (`TP`) to suppress false positives.

### 3.3 Pads Without Net Assignment
A pad lacking net assignment (`net_name == ""` or `net_code == 0`) must be analyzed according to its physical pad type:
- **Plated Through-Hole (PTH) / Surface Mount (SMD):** If an electrical pin on an active component (e.g. `U1` pin 5) has no net, it is either an unrouted electrical signal or an intentional No-Connect (NC). PCB Insight flags this for engineer review.
- **Non-Plated Through-Hole (NPTH):** Used exclusively for mechanical mounting screws and alignment pins. These intentionally carry no net assignment and are classified as **Informational** rather than errors.

---

## 4. PCB Geometry, Layers & Physical Stackup

### 4.1 Layer Roles in Modern Multilayer PCBs
KiCad organizes boards across functional layer planes:
- **Copper Layers (`F.Cu`, `B.Cu`, `In1.Cu`, `In2.Cu`):** Carry signal tracks, power planes, and ground returns.
- **Solder Mask (`F.Mask`, `B.Mask`):** Insulating polymer coating preventing solder bridges between adjacent pads.
- **Silkscreen (`F.Silkscreen`, `B.Silkscreen`):** Visual epoxy ink indicating reference designators, polarities, and component outlines.
- **Edge Cuts (`Edge.Cuts`):** The definitive mechanical milling contour defining the outer physical boundary and internal cutouts of the PCB.

### 4.2 Board Boundary Integrity (`Edge.Cuts`)
A valid PCB must possess a closed, continuous boundary polygon on the `Edge.Cuts` layer. 
- **Missing Outline:** Without an `Edge.Cuts` definition, manufacturing CAM tools cannot compute milling paths, V-score lines, or board panelization dimensions.
- **Dimensions:** The bounding box ($\Delta X = X_{\text{max}} - X_{\text{min}}$, $\Delta Y = Y_{\text{max}} - Y_{\text{min}}$) provides the overall physical size for enclosure fitting and fabricator quoting.

### 4.3 Tracks, Vias, and Zones
- **Tracks:** Conductive copper paths defined by start point, end point, width, layer, and net code.
- **Vias:** Plated holes interconnecting tracks across different copper layers. Parameters include drill diameter and outer copper annular ring width.
- **Zones (Copper Pours):** Continuous copper polygons connected to power or ground planes for low-impedance current return paths and thermal dissipation.
