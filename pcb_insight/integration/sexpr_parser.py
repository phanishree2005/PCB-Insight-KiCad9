"""Pure-Python S-expression parser for KiCad .kicad_pcb files.

Enables robust, headless parsing of board geometry, footprints, pads, nets,
tracks, vias, and zones without requiring a running KiCad desktop session.
Compatible with KiCad 6, 7, 8, and 9 S-expression formats.
"""

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
from pcb_insight.utils.validators import sanitize_string

logger = get_logger()


def tokenize_sexpr(text: str) -> List[str]:
    """Tokenizes S-expression string into parentheses, quoted strings, and atom tokens."""
    token_pattern = re.compile(r'\(|\)|"[^"\\]*(?:\\.[^"\\]*)*"|[^\s()]+')
    return token_pattern.findall(text)


def parse_sexpr_tokens(tokens: List[str]) -> List[Any]:
    """Parses flat token list into a recursive Python nested list structure."""
    stack: List[List[Any]] = [[]]
    for token in tokens:
        if token == "(":
            new_list: List[Any] = []
            stack[-1].append(new_list)
            stack.append(new_list)
        elif token == ")":
            if len(stack) > 1:
                stack.pop()
        else:
            # Strip quotes if string literal
            if token.startswith('"') and token.endswith('"'):
                val = token[1:-1].replace('\\"', '"').replace('\\\\', '\\')
            else:
                val = token
            stack[-1].append(val)
    return stack[0][0] if stack[0] else []


class SExprParserAdapter(BoardAdapter):
    """Parses .kicad_pcb files directly from disk into normalized BoardData."""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path).resolve()

    @property
    def adapter_name(self) -> str:
        return f"SExprFileAdapter({self.file_path.name})"

    def is_available(self) -> bool:
        return self.file_path.exists() and self.file_path.is_file()

    def extract_board_data(self) -> BoardData:
        if not self.is_available():
            raise FileNotFoundError(f"KiCad board file not found: {self.file_path}")

        logger.info(f"Parsing S-expression board file: {self.file_path}")
        try:
            content = self.file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise IOError(f"Failed to read board file: {e}") from e

        tokens = tokenize_sexpr(content)
        if not tokens:
            raise ValueError(f"Board file is empty or contains no tokens: {self.file_path}")

        tree = parse_sexpr_tokens(tokens)
        if not tree or not isinstance(tree, list) or tree[0] != "kicad_pcb":
            raise ValueError(f"Invalid KiCad PCB format. Root node is not 'kicad_pcb'.")

        return self._build_board_data(tree)

    def _build_board_data(self, tree: List[Any]) -> BoardData:
        board_name = self.file_path.stem
        copper_layer_count = 2
        enabled_layers: List[str] = []
        nets: Dict[str, NetData] = {}
        net_code_to_name: Dict[int, str] = {0: ""}
        components: List[ComponentData] = []
        tracks: List[TrackData] = []
        vias: List[ViaData] = []
        zones: List[ZoneData] = []

        edge_cuts_points: List[Tuple[float, float]] = []

        for node in tree[1:]:
            if not isinstance(node, list) or not node:
                continue

            tag = node[0]

            # 1. Parse Layers
            if tag == "layers":
                for layer_entry in node[1:]:
                    if isinstance(layer_entry, list) and len(layer_entry) >= 2:
                        layer_name = sanitize_string(str(layer_entry[1]))
                        enabled_layers.append(layer_name)
                # Count copper layers
                copper_layers = [l for l in enabled_layers if l.endswith(".Cu")]
                if copper_layers:
                    copper_layer_count = len(copper_layers)

            # 2. Parse Net Declarations
            elif tag == "net":
                if len(node) >= 3:
                    try:
                        code = int(node[1])
                        name = sanitize_string(str(node[2]))
                        net_code_to_name[code] = name
                        if name:
                            is_pwr = any(p in name.upper() for p in ("VCC", "+5V", "+3V3", "+12V", "VDD", "PWR"))
                            is_gnd = "GND" in name.upper()
                            nets[name] = NetData(code=code, name=name, is_power=is_pwr, is_ground=is_gnd)
                    except ValueError:
                        pass

            # 3. Parse Footprints (Components)
            elif tag in ("footprint", "module"):
                comp = self._parse_footprint(node, net_code_to_name)
                if comp:
                    components.append(comp)

            # 4. Parse Tracks and Arcs
            elif tag in ("segment", "track"):
                track = self._parse_track(node)
                if track:
                    tracks.append(track)

            # 5. Parse Vias
            elif tag == "via":
                via = self._parse_via(node)
                if via:
                    vias.append(via)

            # 6. Parse Zones
            elif tag == "zone":
                zone = self._parse_zone(node)
                if zone:
                    zones.append(zone)

            # 7. Parse Board Outline Geometry on Edge.Cuts
            elif tag in ("gr_line", "gr_rect", "gr_circle", "gr_arc", "gr_poly"):
                self._collect_outline_points(node, edge_cuts_points)

        # Build net-to-pad references
        for comp in components:
            for pad in comp.pads:
                if pad.net_name and pad.net_name in nets:
                    nets[pad.net_name].pads.append((comp.reference, pad.pad_number))

        # Calculate Board Dimensions and Bounding Box
        has_edge_cuts = len(edge_cuts_points) >= 2
        if has_edge_cuts:
            xs = [p[0] for p in edge_cuts_points]
            ys = [p[1] for p in edge_cuts_points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width = max(0.0, max_x - min_x)
            height = max(0.0, max_y - min_y)
            if width > 0.0 and height > 0.0:
                bbox = (round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3))
                dimensions = (round(width, 3), round(height, 3))
                has_edge_cuts = True
            else:
                has_edge_cuts = False
                bbox = (0.0, 0.0, 0.0, 0.0)
                dimensions = (0.0, 0.0)
        else:
            has_edge_cuts = False
            bbox = (0.0, 0.0, 0.0, 0.0)
            dimensions = (0.0, 0.0)

        return BoardData(
            name=board_name,
            file_path=str(self.file_path),
            dimensions_mm=dimensions,
            bounding_box=bbox,
            copper_layer_count=copper_layer_count,
            enabled_layers=enabled_layers or ["F.Cu", "B.Cu", "Edge.Cuts"],
            components=components,
            nets=nets,
            tracks=tracks,
            vias=vias,
            zones=zones,
            has_edge_cuts=has_edge_cuts,
        )

    def _parse_footprint(self, node: List[Any], net_lookup: Dict[int, str]) -> Optional[ComponentData]:
        fp_id = sanitize_string(str(node[1])) if len(node) > 1 else ""
        ref = ""
        val = ""
        layer = "F.Cu"
        pos_x, pos_y = 0.0, 0.0
        orientation = 0.0
        pads: List[PadData] = []
        is_dnp = False

        for item in node[2:]:
            if not isinstance(item, list) or not item:
                continue

            subtag = item[0]

            if subtag == "layer" and len(item) > 1:
                layer = sanitize_string(str(item[1]))

            elif subtag == "at" and len(item) >= 3:
                try:
                    pos_x = float(item[1])
                    pos_y = float(item[2])
                    if len(item) >= 4:
                        orientation = float(item[3])
                except ValueError:
                    pass

            elif subtag in ("property", "fp_text"):
                # (property "Reference" "R1" ...) or (fp_text reference "R1" ...)
                prop_key = str(item[1]).strip().lower() if len(item) > 1 else ""
                prop_val = sanitize_string(str(item[2])) if len(item) > 2 else ""

                if "reference" in prop_key:
                    ref = prop_val
                elif "value" in prop_key:
                    val = prop_val
                elif "dnp" in prop_key and prop_val.lower() in ("yes", "true", "1"):
                    is_dnp = True

            elif subtag == "attr" and len(item) > 1:
                attr_val = str(item[1]).lower()
                if "dnp" in attr_val:
                    is_dnp = True

            elif subtag == "pad":
                pad = self._parse_pad(item, net_lookup, ref)
                if pad:
                    pads.append(pad)

        # Compute reference prefix (e.g. "R12" -> "R", "U3" -> "U")
        prefix_match = re.match(r"^([A-Za-z]+)", ref)
        prefix = prefix_match.group(1).upper() if prefix_match else ""

        return ComponentData(
            reference=ref,
            prefix=prefix,
            value=val,
            footprint_name=fp_id,
            layer=layer,
            position_x_mm=round(pos_x, 3),
            position_y_mm=round(pos_y, 3),
            orientation_deg=round(orientation, 2),
            pads=pads,
            is_dnp=is_dnp,
        )

    def _parse_pad(self, node: List[Any], net_lookup: Dict[int, str], parent_ref: str) -> Optional[PadData]:
        # (pad "1" smd roundrect (at -0.95 0) (size 1.0 1.3) (layers "F.Cu" ...) (net 2 "+3V3"))
        if len(node) < 3:
            return None

        pad_num = sanitize_string(str(node[1]))
        pad_type = str(node[2]).upper()  # smd, thru_hole, np_thru_hole, connect
        pos_x, pos_y = 0.0, 0.0
        size_x, size_y = 0.0, 0.0
        pad_layers: List[str] = []
        net_code = 0
        net_name = ""

        for item in node[3:]:
            if not isinstance(item, list) or not item:
                continue

            subtag = item[0]
            if subtag == "at" and len(item) >= 3:
                try:
                    pos_x = float(item[1])
                    pos_y = float(item[2])
                except ValueError:
                    pass
            elif subtag == "size" and len(item) >= 3:
                try:
                    size_x = float(item[1])
                    size_y = float(item[2])
                except ValueError:
                    pass
            elif subtag == "layers":
                pad_layers = [sanitize_string(str(l)) for l in item[1:]]
            elif subtag == "net" and len(item) >= 2:
                try:
                    net_code = int(item[1])
                    if len(item) >= 3:
                        net_name = sanitize_string(str(item[2]))
                    else:
                        net_name = net_lookup.get(net_code, "")
                except ValueError:
                    pass

        return PadData(
            pad_number=pad_num,
            net_name=net_name,
            net_code=net_code,
            pad_type=pad_type,
            position_x_mm=round(pos_x, 3),
            position_y_mm=round(pos_y, 3),
            size_x_mm=round(size_x, 3),
            size_y_mm=round(size_y, 3),
            layers=tuple(pad_layers) if pad_layers else ("F.Cu",),
            parent_reference=parent_ref,
        )

    def _parse_track(self, node: List[Any]) -> Optional[TrackData]:
        # (segment (start x y) (end x y) (width w) (layer l) (net n))
        start_x, start_y = 0.0, 0.0
        end_x, end_y = 0.0, 0.0
        width = 0.25
        layer = "F.Cu"
        net_code = 0

        for item in node[1:]:
            if not isinstance(item, list) or not item:
                continue
            subtag = item[0]
            if subtag == "start" and len(item) >= 3:
                try:
                    start_x, start_y = float(item[1]), float(item[2])
                except ValueError:
                    pass
            elif subtag == "end" and len(item) >= 3:
                try:
                    end_x, end_y = float(item[1]), float(item[2])
                except ValueError:
                    pass
            elif subtag == "width" and len(item) >= 2:
                try:
                    width = float(item[1])
                except ValueError:
                    pass
            elif subtag == "layer" and len(item) >= 2:
                layer = sanitize_string(str(item[1]))
            elif subtag == "net" and len(item) >= 2:
                try:
                    net_code = int(item[1])
                except ValueError:
                    pass

        return TrackData(
            start_x_mm=round(start_x, 3),
            start_y_mm=round(start_y, 3),
            end_x_mm=round(end_x, 3),
            end_y_mm=round(end_y, 3),
            width_mm=round(width, 3),
            layer=layer,
            net_code=net_code,
        )

    def _parse_via(self, node: List[Any]) -> Optional[ViaData]:
        # (via (at x y) (size s) (drill d) (layers l1 l2) (net n))
        pos_x, pos_y = 0.0, 0.0
        size = 0.8
        drill = 0.4
        via_layers = ("F.Cu", "B.Cu")
        net_code = 0

        for item in node[1:]:
            if not isinstance(item, list) or not item:
                continue
            subtag = item[0]
            if subtag == "at" and len(item) >= 3:
                try:
                    pos_x, pos_y = float(item[1]), float(item[2])
                except ValueError:
                    pass
            elif subtag == "size" and len(item) >= 2:
                try:
                    size = float(item[1])
                except ValueError:
                    pass
            elif subtag == "drill" and len(item) >= 2:
                try:
                    drill = float(item[1])
                except ValueError:
                    pass
            elif subtag == "layers" and len(item) >= 3:
                via_layers = (sanitize_string(str(item[1])), sanitize_string(str(item[2])))
            elif subtag == "net" and len(item) >= 2:
                try:
                    net_code = int(item[1])
                except ValueError:
                    pass

        return ViaData(
            position_x_mm=round(pos_x, 3),
            position_y_mm=round(pos_y, 3),
            size_mm=round(size, 3),
            drill_mm=round(drill, 3),
            layers=via_layers,
            net_code=net_code,
        )

    def _parse_zone(self, node: List[Any]) -> Optional[ZoneData]:
        net_name = ""
        net_code = 0
        layer = "F.Cu"
        name = ""

        for item in node[1:]:
            if not isinstance(item, list) or not item:
                continue
            subtag = item[0]
            if subtag == "net" and len(item) >= 2:
                try:
                    net_code = int(item[1])
                except ValueError:
                    pass
            elif subtag == "net_name" and len(item) >= 2:
                net_name = sanitize_string(str(item[1]))
            elif subtag == "layer" and len(item) >= 2:
                layer = sanitize_string(str(item[1]))
            elif subtag == "name" and len(item) >= 2:
                name = sanitize_string(str(item[1]))

        return ZoneData(
            name=name,
            net_name=net_name,
            net_code=net_code,
            layer=layer,
            is_filled=True,
        )

    def _collect_outline_points(self, node: List[Any], points: List[Tuple[float, float]]):
        """Extracts coordinate points from graphical elements on Edge.Cuts layer.
        
        Supports gr_line, gr_rect, gr_circle, gr_arc, gr_poly, and gr_curve.
        """
        # Find layer
        layer = ""
        for item in node[1:]:
            if isinstance(item, list) and len(item) >= 2 and item[0] == "layer":
                layer = sanitize_string(str(item[1]))
                break

        if layer != "Edge.Cuts":
            return

        tag = node[0]
        if tag in ("gr_line", "gr_rect"):
            for item in node[1:]:
                if isinstance(item, list) and len(item) >= 3 and item[0] in ("start", "end"):
                    try:
                        points.append((float(item[1]), float(item[2])))
                    except ValueError:
                        pass
        elif tag == "gr_circle":
            center: Optional[Tuple[float, float]] = None
            end_pt: Optional[Tuple[float, float]] = None
            for item in node[1:]:
                if isinstance(item, list) and len(item) >= 3:
                    if item[0] == "center":
                        try:
                            center = (float(item[1]), float(item[2]))
                        except ValueError:
                            pass
                    elif item[0] == "end":
                        try:
                            end_pt = (float(item[1]), float(item[2]))
                        except ValueError:
                            pass
            if center and end_pt:
                r = math.hypot(end_pt[0] - center[0], end_pt[1] - center[1])
                points.append((center[0] - r, center[1] - r))
                points.append((center[0] + r, center[1] + r))
            elif center:
                points.append(center)
        elif tag == "gr_arc":
            for item in node[1:]:
                if isinstance(item, list) and len(item) >= 3 and item[0] in ("start", "mid", "end"):
                    try:
                        points.append((float(item[1]), float(item[2])))
                    except ValueError:
                        pass
        elif tag == "gr_poly":
            for item in node[1:]:
                if isinstance(item, list) and item[0] == "pts":
                    for pt_node in item[1:]:
                        if isinstance(pt_node, list) and len(pt_node) >= 3 and pt_node[0] == "xy":
                            try:
                                points.append((float(pt_node[1]), float(pt_node[2])))
                            except ValueError:
                                pass
        elif tag == "gr_curve":
            for item in node[1:]:
                if isinstance(item, list) and item[0] == "pts":
                    for pt_node in item[1:]:
                        if isinstance(pt_node, list) and len(pt_node) >= 3 and pt_node[0] == "xy":
                            try:
                                points.append((float(pt_node[1]), float(pt_node[2])))
                            except ValueError:
                                pass
