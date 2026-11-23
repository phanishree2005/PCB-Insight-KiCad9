"""Component and Bill of Materials (BOM) Analysis Engine.

Performs deep metadata audits on components: IEEE prefix classification,
layer distribution, duplicate reference detection, missing values, and
footprint consistency checks.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from pcb_insight.core.data_models import BoardData, ComponentData
from pcb_insight.utils.logging_config import get_logger
from pcb_insight.utils.validators import validate_reference_format

logger = get_logger()

# Standard IEEE 315 / IEEE 200 prefix classifications
PREFIX_DESCRIPTIONS: Dict[str, str] = {
    "R": "Resistors",
    "C": "Capacitors",
    "L": "Inductors / Chokes",
    "D": "Diodes / LEDs / Rectifiers",
    "Q": "Transistors / MOSFETs",
    "U": "Integrated Circuits (ICs)",
    "IC": "Integrated Circuits (ICs)",
    "J": "Connectors / Jacks",
    "P": "Pin Headers / Plugs",
    "SW": "Switches / Pushbuttons",
    "TP": "Test Points",
    "Y": "Crystals / Oscillators",
    "F": "Fuses",
    "T": "Transformers",
    "H": "Mounting Holes / Hardware",
    "MH": "Mounting Holes",
    "FID": "Fiducial Optical Markers",
    "BT": "Batteries",
    "RV": "Potentiometers / Varistors",
}


@dataclass
class ComponentAnalysisReport:
    """Aggregated analytical summary of all components on the board."""
    total_components: int
    prefix_counts: Dict[str, int] = field(default_factory=dict)
    prefix_descriptions: Dict[str, str] = field(default_factory=dict)
    layer_distribution: Dict[str, int] = field(default_factory=dict)
    footprint_counts: Dict[str, int] = field(default_factory=dict)
    dnp_count: int = 0
    duplicate_references: Dict[str, List[ComponentData]] = field(default_factory=dict)
    missing_references: List[ComponentData] = field(default_factory=list)
    placeholder_references: List[ComponentData] = field(default_factory=list)
    missing_values: List[ComponentData] = field(default_factory=list)
    missing_footprints: List[ComponentData] = field(default_factory=list)


class ComponentAnalyzer:
    """Evaluates component metadata hygiene and statistical distribution."""

    def __init__(self, board: BoardData):
        self.board = board

    def analyze(self) -> ComponentAnalysisReport:
        """Executes full component auditing pipeline."""
        comps = self.board.components
        total = len(comps)

        prefix_counter: Counter = Counter()
        layer_counter: Counter = Counter()
        footprint_counter: Counter = Counter()
        ref_map: Dict[str, List[ComponentData]] = defaultdict(list)

        missing_refs: List[ComponentData] = []
        placeholder_refs: List[ComponentData] = []
        missing_values: List[ComponentData] = []
        missing_footprints: List[ComponentData] = []
        dnp_count = 0

        for c in comps:
            # Prefix counting
            p = c.prefix.upper() or "OTHER"
            prefix_counter[p] += 1

            # Layer counting
            layer_counter[c.layer] += 1

            # Footprint counting
            fp = c.footprint_name or "(None)"
            footprint_counter[fp] += 1

            # DNP counting
            if c.is_dnp:
                dnp_count += 1

            # Reference designator validation
            ref = c.reference.strip()
            if not ref:
                missing_refs.append(c)
            else:
                ref_map[ref.upper()].append(c)
                is_valid, reason = validate_reference_format(ref)
                if not is_valid:
                    placeholder_refs.append(c)

            # Value validation
            val = c.value.strip()
            if not val or val in ("~", "Value", "val", "(None)"):
                # Exclude test points, fiducials, and mounting holes from missing value checks
                if not (c.is_test_point or c.is_mounting_hole or p == "FID"):
                    missing_values.append(c)

            # Footprint validation
            if not c.footprint_name or not c.footprint_name.strip():
                missing_footprints.append(c)

        # Detect duplicates
        duplicates = {ref: items for ref, items in ref_map.items() if len(items) > 1}

        # Resolve prefix descriptions
        p_desc = {p: PREFIX_DESCRIPTIONS.get(p, "Miscellaneous Electronics") for p in prefix_counter}

        return ComponentAnalysisReport(
            total_components=total,
            prefix_counts=dict(prefix_counter.most_common()),
            prefix_descriptions=p_desc,
            layer_distribution=dict(layer_counter),
            footprint_counts=dict(footprint_counter.most_common()),
            dnp_count=dnp_count,
            duplicate_references=duplicates,
            missing_references=missing_refs,
            placeholder_references=placeholder_refs,
            missing_values=missing_values,
            missing_footprints=missing_footprints,
        )
