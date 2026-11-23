"""Electrical Net and Topological Connectivity Analysis Engine.

Audits electrical connectivity across pads and nets: builds inverted net-pad
index, flags single-pin net antenna risks, identifies empty net definitions,
and audits unassigned pads while distinguishing intentional mechanical holes.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from pcb_insight.core.data_models import BoardData, NetData, PadData
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


@dataclass
class ConnectivityAnalysisReport:
    """Aggregated connectivity findings and net topology metrics."""
    total_nets: int
    power_nets: List[str] = field(default_factory=list)
    ground_nets: List[str] = field(default_factory=list)
    single_pin_nets: List[NetData] = field(default_factory=list)
    empty_nets: List[NetData] = field(default_factory=list)
    connected_pad_count: int = 0
    unconnected_pad_count: int = 0
    mechanical_unconnected_pads: List[PadData] = field(default_factory=list)
    electrical_unconnected_pads: List[PadData] = field(default_factory=list)
    net_pad_matrix: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)


class ConnectivityAnalyzer:
    """Constructs and analyzes the electrical net-to-pad topological graph."""

    def __init__(self, board: BoardData):
        self.board = board

    def analyze(self) -> ConnectivityAnalysisReport:
        """Executes electrical connectivity auditing pipeline."""
        nets = self.board.nets
        components = self.board.components

        # Build comprehensive net-to-pad map
        net_to_pads: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        all_pads: List[PadData] = []

        for c in components:
            for pad in c.pads:
                all_pads.append(pad)
                if pad.net_name and pad.net_name.strip():
                    net_to_pads[pad.net_name].append((c.reference, pad.pad_number))

        # Ensure all defined board nets exist in net_to_pads
        for net_name in nets:
            if net_name not in net_to_pads:
                net_to_pads[net_name] = []

        power_nets: List[str] = []
        ground_nets: List[str] = []
        single_pin_nets: List[NetData] = []
        empty_nets: List[NetData] = []

        for net_name, pad_list in net_to_pads.items():
            net_obj = nets.get(net_name, NetData(code=0, name=net_name, pads=pad_list))
            net_obj.pads = pad_list

            upper_name = net_name.upper()
            if any(p in upper_name for p in ("VCC", "+5V", "+3V3", "+12V", "VDD", "PWR", "VBAT")):
                power_nets.append(net_name)
            if "GND" in upper_name:
                ground_nets.append(net_name)

            if len(pad_list) == 1:
                # Check if the single pad belongs to an intentional test point
                ref, pad_num = pad_list[0]
                if not (ref.upper().startswith("TP") or "TEST" in ref.upper()):
                    single_pin_nets.append(net_obj)

            elif len(pad_list) == 0:
                empty_nets.append(net_obj)

        # Audit Unconnected / Unassigned Pads
        connected_count = 0
        unconnected_count = 0
        mech_unconnected: List[PadData] = []
        elec_unconnected: List[PadData] = []

        for pad in all_pads:
            if pad.is_connected:
                connected_count += 1
            else:
                unconnected_count += 1
                if pad.is_mechanical_only:
                    mech_unconnected.append(pad)
                else:
                    # Check if parent is mounting hole or fiducial
                    parent_ref = pad.parent_reference.upper()
                    if parent_ref.startswith("H") or parent_ref.startswith("MH") or parent_ref.startswith("FID"):
                        mech_unconnected.append(pad)
                    else:
                        elec_unconnected.append(pad)

        return ConnectivityAnalysisReport(
            total_nets=len(net_to_pads),
            power_nets=sorted(power_nets),
            ground_nets=sorted(ground_nets),
            single_pin_nets=single_pin_nets,
            empty_nets=empty_nets,
            connected_pad_count=connected_count,
            unconnected_pad_count=unconnected_count,
            mechanical_unconnected_pads=mech_unconnected,
            electrical_unconnected_pads=elec_unconnected,
            net_pad_matrix=dict(net_to_pads),
        )
