"""Strongly-typed normalized data models for PCB Insight.

Decouples internal analysis engines and reporting systems from KiCad-specific
data structures (whether Protobuf from the IPC API, C++ pointers from SWIG,
or nested tokens from raw S-expressions).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class FindingSeverity(str, Enum):
    """Severity classification for analysis findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class PadData:
    """Represents a physical component pad."""
    pad_number: str
    net_name: str = ""
    net_code: int = 0
    pad_type: str = "SMD"  # SMD, PTH (through_hole), NPTH (np_thru_hole), CONNECT
    position_x_mm: float = 0.0
    position_y_mm: float = 0.0
    size_x_mm: float = 0.0
    size_y_mm: float = 0.0
    layers: Tuple[str, ...] = ("F.Cu",)
    parent_reference: str = ""

    @property
    def is_connected(self) -> bool:
        """Determines if the pad has an assigned non-empty electrical net."""
        return bool(self.net_name and self.net_name.strip() and self.net_code > 0)

    @property
    def is_mechanical_only(self) -> bool:
        """Determines if the pad is purely mechanical (Non-Plated Through-Hole)."""
        t = self.pad_type.lower()
        return "npth" in t or "np_thru" in t


@dataclass
class ComponentData:
    """Represents an electronic component / footprint instance on the board."""
    reference: str
    prefix: str
    value: str = ""
    footprint_name: str = ""
    layer: str = "F.Cu"
    position_x_mm: float = 0.0
    position_y_mm: float = 0.0
    orientation_deg: float = 0.0
    pads: List[PadData] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    is_dnp: bool = False  # Do Not Populate

    @property
    def pad_count(self) -> int:
        return len(self.pads)

    @property
    def connected_pad_count(self) -> int:
        return sum(1 for p in self.pads if p.is_connected)

    @property
    def is_test_point(self) -> bool:
        return self.prefix.upper() == "TP" or "test_point" in self.footprint_name.lower()

    @property
    def is_mounting_hole(self) -> bool:
        return self.prefix.upper() in ("H", "MH") or "mountinghole" in self.footprint_name.lower()


@dataclass
class NetData:
    """Represents an electrical net and its topological connections."""
    code: int
    name: str
    pads: List[Tuple[str, str]] = field(default_factory=list)  # [(ref, pad_number), ...]
    is_power: bool = False
    is_ground: bool = False

    @property
    def pad_count(self) -> int:
        return len(self.pads)

    @property
    def is_single_pin(self) -> bool:
        return len(self.pads) == 1

    @property
    def is_empty(self) -> bool:
        return len(self.pads) == 0


@dataclass(frozen=True)
class TrackData:
    """Represents a routed copper track segment."""
    start_x_mm: float
    start_y_mm: float
    end_x_mm: float
    end_y_mm: float
    width_mm: float
    layer: str
    net_code: int = 0


@dataclass(frozen=True)
class ViaData:
    """Represents an interlayer via."""
    position_x_mm: float
    position_y_mm: float
    size_mm: float
    drill_mm: float
    layers: Tuple[str, str] = ("F.Cu", "B.Cu")
    net_code: int = 0
    via_type: str = "through"


@dataclass(frozen=True)
class ZoneData:
    """Represents a copper pour zone."""
    name: str
    net_name: str
    net_code: int
    layer: str
    is_filled: bool = False


@dataclass
class BoardData:
    """Normalized top-level container for all extracted PCB data."""
    name: str = "Untitled"
    file_path: Optional[str] = None
    dimensions_mm: Tuple[float, float] = (0.0, 0.0)  # width, height
    bounding_box: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # min_x, min_y, max_x, max_y
    copper_layer_count: int = 2
    enabled_layers: List[str] = field(default_factory=lambda: ["F.Cu", "B.Cu", "Edge.Cuts"])
    components: List[ComponentData] = field(default_factory=list)
    nets: Dict[str, NetData] = field(default_factory=dict)
    tracks: List[TrackData] = field(default_factory=list)
    vias: List[ViaData] = field(default_factory=list)
    zones: List[ZoneData] = field(default_factory=list)
    has_edge_cuts: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def net_count(self) -> int:
        return len(self.nets)

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    @property
    def via_count(self) -> int:
        return len(self.vias)

    @property
    def zone_count(self) -> int:
        return len(self.zones)


@dataclass
class AnalysisFinding:
    """Represents an explainable finding produced by an analysis rule or native DRC."""
    rule_id: str
    rule_name: str
    severity: FindingSeverity
    title: str
    explanation: str
    remediation: str
    affected_components: List[str] = field(default_factory=list)
    affected_nets: List[str] = field(default_factory=list)
    source: str = "PCB_Insight"  # "PCB_Insight" or "KiCad_Native_DRC"
    raw_data: Optional[Dict] = None


@dataclass
class AnalysisResult:
    """Container holding all findings, summaries, and extracted board statistics."""
    board: BoardData
    findings: List[AnalysisFinding] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    timestamp_iso: str = ""
    native_drc_executed: bool = False
    native_drc_output: Optional[str] = None

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.INFO)

    @property
    def total_findings(self) -> int:
        return len(self.findings)
