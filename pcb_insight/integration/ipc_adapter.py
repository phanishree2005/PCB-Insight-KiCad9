"""KiCad 9 official IPC API adapter using kicad-python (kipy).

Connects to a running KiCad 9 instance over Nanomsg-NG (Named Pipes on Windows,
Unix Domain Sockets on Linux/macOS) and extracts live PCB design data.
"""

import os
from typing import Dict, List, Optional, Tuple

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


class IPCClientAdapter(BoardAdapter):
    """Adapter for extracting board data from a running KiCad 9 session via IPC API."""

    def __init__(self, socket_path: Optional[str] = None, kicad_token: Optional[str] = None):
        self.socket_path = socket_path or os.environ.get("KICAD_API_SOCKET")
        self.kicad_token = kicad_token or os.environ.get("KICAD_API_TOKEN", "")
        self._client = None
        self._kicad = None

    @property
    def adapter_name(self) -> str:
        return "KiCad9_IPC_Adapter"

    def is_available(self) -> bool:
        """Checks if kicad-python is installed and a live KiCad API server responds to ping."""
        try:
            from kipy.kicad import KiCad  # type: ignore
            kicad = KiCad(socket_path=self.socket_path, kicad_token=self.kicad_token, timeout_ms=800)
            kicad.ping()
            self._kicad = kicad
            return True
        except Exception as e:
            logger.debug(f"KiCad IPC server is not reachable: {e}")
            return False

    def get_kicad_cli_path(self) -> Optional[str]:
        """Resolves the absolute path to kicad-cli using KiCad's internal resolver."""
        try:
            if self._kicad or self.is_available():
                return self._kicad.get_kicad_binary_path("kicad-cli")
        except Exception as e:
            logger.debug(f"Could not query KiCad binary path over IPC: {e}")
        return None

    def extract_board_data(self) -> BoardData:
        """Extracts live PCB layout from KiCad 9 over Protocol Buffers."""
        if not self.is_available() or self._kicad is None:
            raise ConnectionError(
                "Cannot connect to KiCad 9 IPC server. Please ensure KiCad 9 is open "
                "and 'Enable API Server' is checked in Preferences > Plugins."
            )

        logger.info("Extracting live board data from KiCad 9 via IPC API...")
        try:
            board = self._kicad.get_board()
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve open board from KiCad: {e}") from e

        board_name = board.name() or "Active Board"
        copper_layers = board.get_copper_layer_count()
        raw_layers = board.get_enabled_layers()
        enabled_layers = [str(l) for l in raw_layers]

        # 1. Extract Footprints & Components
        components: List[ComponentData] = []
        try:
            raw_footprints = board.get_footprints()
        except Exception as e:
            logger.warning(f"Error querying footprints over IPC: {e}")
            raw_footprints = []

        for fp in raw_footprints:
            ref = fp.reference_field.text.text if fp.reference_field and hasattr(fp.reference_field, "text") else ""
            val = fp.value_field.text.text if fp.value_field and hasattr(fp.value_field, "text") else ""
            fp_id = str(fp.definition.id) if fp.definition and hasattr(fp.definition, "id") else ""
            pos = fp.position
            layer = str(fp.layer) if hasattr(fp, "layer") else "F.Cu"
            orientation = getattr(fp.orientation, "degrees", 0.0) if hasattr(fp, "orientation") else 0.0

            # Extract pads from fp.definition.items (KiCad 9 verified path)
            pads: List[PadData] = []
            if fp.definition and hasattr(fp.definition, "items"):
                for item in fp.definition.items:
                    if hasattr(item, "number") and hasattr(item, "net"):
                        pad_num = str(item.number)
                        net_name = item.net.name if item.net and hasattr(item.net, "name") else ""
                        net_code = item.net.code if item.net and hasattr(item.net, "code") else 0
                        pad_type = str(getattr(item, "pad_type", "SMD"))
                        
                        pad_pos = getattr(item, "position", None)
                        px = pad_pos.x / 1_000_000.0 if pad_pos else 0.0
                        py = pad_pos.y / 1_000_000.0 if pad_pos else 0.0

                        pad_size = getattr(item, "size", None)
                        sx = pad_size.x / 1_000_000.0 if pad_size else 0.0
                        sy = pad_size.y / 1_000_000.0 if pad_size else 0.0

                        pads.append(PadData(
                            pad_number=pad_num,
                            net_name=net_name,
                            net_code=net_code,
                            pad_type=pad_type,
                            position_x_mm=round(px, 3),
                            position_y_mm=round(py, 3),
                            size_x_mm=round(sx, 3),
                            size_y_mm=round(sy, 3),
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
                position_x_mm=round(pos.x / 1_000_000.0, 3) if pos else 0.0,
                position_y_mm=round(pos.y / 1_000_000.0, 3) if pos else 0.0,
                orientation_deg=round(orientation, 2),
                pads=pads,
            ))

        # 2. Extract Nets
        nets: Dict[str, NetData] = {}
        try:
            raw_nets = board.get_nets()
            for net in raw_nets:
                name = getattr(net, "name", "")
                code = getattr(net, "code", 0)
                if name:
                    is_pwr = any(p in name.upper() for p in ("VCC", "+5V", "+3V3", "+12V", "VDD", "PWR"))
                    is_gnd = "GND" in name.upper()
                    nets[name] = NetData(code=code, name=name, is_power=is_pwr, is_ground=is_gnd)
        except Exception as e:
            logger.warning(f"Error querying nets over IPC: {e}")

        # Map pads to nets
        for comp in components:
            for pad in comp.pads:
                if pad.net_name and pad.net_name in nets:
                    nets[pad.net_name].pads.append((comp.reference, pad.pad_number))

        # 3. Extract Tracks
        tracks: List[TrackData] = []
        try:
            for t in board.get_tracks():
                start = getattr(t, "start", None)
                end = getattr(t, "end", None)
                tracks.append(TrackData(
                    start_x_mm=round(start.x / 1_000_000.0, 3) if start else 0.0,
                    start_y_mm=round(start.y / 1_000_000.0, 3) if start else 0.0,
                    end_x_mm=round(end.x / 1_000_000.0, 3) if end else 0.0,
                    end_y_mm=round(end.y / 1_000_000.0, 3) if end else 0.0,
                    width_mm=round(getattr(t, "width", 250_000) / 1_000_000.0, 3),
                    layer=str(getattr(t, "layer", "F.Cu")),
                    net_code=getattr(getattr(t, "net", None), "code", 0),
                ))
        except Exception as e:
            logger.debug(f"Tracks extraction over IPC: {e}")

        # 4. Extract Vias
        vias: List[ViaData] = []
        try:
            for v in board.get_vias():
                pos = getattr(v, "position", None)
                vias.append(ViaData(
                    position_x_mm=round(pos.x / 1_000_000.0, 3) if pos else 0.0,
                    position_y_mm=round(pos.y / 1_000_000.0, 3) if pos else 0.0,
                    size_mm=round(getattr(v, "width", 800_000) / 1_000_000.0, 3),
                    drill_mm=round(getattr(v, "drill", 400_000) / 1_000_000.0, 3),
                    layers=("F.Cu", "B.Cu"),
                    net_code=getattr(getattr(v, "net", None), "code", 0),
                ))
        except Exception as e:
            logger.debug(f"Vias extraction over IPC: {e}")

        # 5. Extract Zones
        zones: List[ZoneData] = []
        try:
            for z in board.get_zones():
                net = getattr(z, "net", None)
                zones.append(ZoneData(
                    name=getattr(z, "name", "") or "",
                    net_name=getattr(net, "name", "") if net else "",
                    net_code=getattr(net, "code", 0) if net else 0,
                    layer=str(getattr(z, "layer", "F.Cu")),
                    is_filled=True,
                ))
        except Exception as e:
            logger.debug(f"Zones extraction over IPC: {e}")

        # 6. Extract Board Boundary / Dimensions
        edge_cuts_points: List[Tuple[float, float]] = []
        try:
            for s in board.get_shapes():
                if "Edge_Cuts" in str(getattr(s, "layer", "")) or "Edge.Cuts" in str(getattr(s, "layer", "")):
                    start = getattr(s, "start", None)
                    end = getattr(s, "end", None)
                    if start:
                        edge_cuts_points.append((start.x / 1_000_000.0, start.y / 1_000_000.0))
                    if end:
                        edge_cuts_points.append((end.x / 1_000_000.0, end.y / 1_000_000.0))
        except Exception as e:
            logger.debug(f"Shapes extraction over IPC: {e}")

        has_edge_cuts = len(edge_cuts_points) >= 2
        if has_edge_cuts:
            xs = [p[0] for p in edge_cuts_points]
            ys = [p[1] for p in edge_cuts_points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            bbox = (round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3))
            dimensions = (round(max_x - min_x, 3), round(max_y - min_y, 3))
        else:
            bbox = (0.0, 0.0, 0.0, 0.0)
            dimensions = (0.0, 0.0)

        return BoardData(
            name=board_name,
            file_path=None,
            dimensions_mm=dimensions,
            bounding_box=bbox,
            copper_layer_count=copper_layers,
            enabled_layers=enabled_layers or ["F.Cu", "B.Cu", "Edge.Cuts"],
            components=components,
            nets=nets,
            tracks=tracks,
            vias=vias,
            zones=zones,
            has_edge_cuts=has_edge_cuts,
        )
