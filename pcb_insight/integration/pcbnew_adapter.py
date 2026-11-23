"""Legacy pcbnew ActionPlugin fallback adapter for KiCad 9.

Operates in-process inside KiCad's internal Python interpreter when launched
from Tools > External Plugins > PCB Insight.
"""

from typing import Dict, List, Optional
from pcb_insight.core.data_models import (
    BoardData,
    ComponentData,
    NetData,
    PadData,
    TrackData,
    ViaData,
    ZoneData,
)
from pcb_insight.integration.adapter_interface import BoardAdapter
from pcb_insight.utils.logging_config import get_logger

logger = get_logger()


class PcbnewAdapter(BoardAdapter):
    """Adapter that extracts board data using the legacy in-process pcbnew C++ bindings."""

    def __init__(self, board_instance=None):
        self._board = board_instance

    @property
    def adapter_name(self) -> str:
        return "Legacy_pcbnew_Adapter"

    def is_available(self) -> bool:
        """Checks if pcbnew module can be imported in the current Python runtime."""
        try:
            import pcbnew  # type: ignore
            return True
        except ImportError:
            return False

    def extract_board_data(self) -> BoardData:
        """Extracts data from the active pcbnew.BOARD pointer."""
        if not self.is_available():
            raise ImportError("pcbnew module is not available in this Python interpreter.")

        import pcbnew  # type: ignore

        board = self._board or pcbnew.GetBoard()
        if not board:
            raise RuntimeError("No active board currently loaded in pcbnew.")

        file_name = board.GetFileName() or "Active Board"
        copper_count = board.GetCopperLayerCount()

        # Extract Footprints
        components: List[ComponentData] = []
        for fp in board.GetFootprints():
            ref = fp.GetReference() or ""
            val = fp.GetValue() or ""
            fp_id = fp.GetFPIDAsString() or ""
            pos = fp.GetPosition()
            layer = board.GetLayerName(fp.GetLayer())

            pads: List[PadData] = []
            for pad in fp.Pads():
                pad_num = pad.GetNumber() or ""
                net_name = pad.GetNetname() or ""
                net_code = pad.GetNetCode()
                pad_type = str(pad.GetAttribute())
                pad_pos = pad.GetPosition()

                pads.append(PadData(
                    pad_number=pad_num,
                    net_name=net_name,
                    net_code=net_code,
                    pad_type=pad_type,
                    position_x_mm=round(pcbnew.ToMM(pad_pos.x), 3),
                    position_y_mm=round(pcbnew.ToMM(pad_pos.y), 3),
                    layers=(layer,),
                    parent_reference=ref,
                ))

            prefix = ref.rstrip("0123456789").upper()
            components.append(ComponentData(
                reference=ref,
                prefix=prefix,
                value=val,
                footprint_name=fp_id,
                layer=layer,
                position_x_mm=round(pcbnew.ToMM(pos.x), 3),
                position_y_mm=round(pcbnew.ToMM(pos.y), 3),
                orientation_deg=round(fp.GetOrientationDegrees(), 2),
                pads=pads,
            ))

        # Extract Nets
        nets: Dict[str, NetData] = {}
        net_info = board.GetNetInfo()
        for i in range(net_info.GetCount()):
            net_item = net_info.GetNetItem(i)
            net_name = net_item.GetNetname()
            net_code = net_item.GetNetCode()
            if net_name:
                is_pwr = any(p in net_name.upper() for p in ("VCC", "+5V", "+3V3", "+12V", "VDD"))
                is_gnd = "GND" in net_name.upper()
                nets[net_name] = NetData(code=net_code, name=net_name, is_power=is_pwr, is_ground=is_gnd)

        # Map pads to nets
        for comp in components:
            for pad in comp.pads:
                if pad.net_name and pad.net_name in nets:
                    nets[pad.net_name].pads.append((comp.reference, pad.pad_number))

        # Extract Dimensions from Bounding Box
        bbox_box = board.GetBoardEdgesBoundingBox()
        w_mm = round(pcbnew.ToMM(bbox_box.GetWidth()), 3)
        h_mm = round(pcbnew.ToMM(bbox_box.GetHeight()), 3)
        min_x = round(pcbnew.ToMM(bbox_box.GetX()), 3)
        min_y = round(pcbnew.ToMM(bbox_box.GetY()), 3)

        return BoardData(
            name=file_name,
            file_path=file_name,
            dimensions_mm=(w_mm, h_mm),
            bounding_box=(min_x, min_y, min_x + w_mm, min_y + h_mm),
            copper_layer_count=copper_count,
            enabled_layers=["F.Cu", "B.Cu", "Edge.Cuts"],
            components=components,
            nets=nets,
            tracks=[],
            vias=[],
            zones=[],
            has_edge_cuts=(w_mm > 0.0 and h_mm > 0.0),
        )
