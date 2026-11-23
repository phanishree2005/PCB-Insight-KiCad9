"""Unit tests for normalized data models and validators."""

import pytest
from pcb_insight.core.data_models import (
    BoardData,
    ComponentData,
    FindingSeverity,
    NetData,
    PadData,
    TrackData,
    ViaData,
)
from pcb_insight.utils.validators import validate_reference_format, sanitize_string


def test_pad_connectivity():
    p1 = PadData(pad_number="1", net_name="GND", net_code=1)
    assert p1.is_connected is True
    assert p1.is_mechanical_only is False

    p2 = PadData(pad_number="2", net_name="", net_code=0)
    assert p2.is_connected is False

    p3 = PadData(pad_number="3", net_name="", net_code=0, pad_type="NPTH")
    assert p3.is_mechanical_only is True


def test_component_properties():
    pads = [
        PadData(pad_number="1", net_name="GND", net_code=1),
        PadData(pad_number="2", net_name="+5V", net_code=2),
    ]
    c = ComponentData(
        reference="R1",
        prefix="R",
        value="10k",
        footprint_name="Resistor_SMD:R_0805",
        pads=pads,
    )
    assert c.pad_count == 2
    assert c.connected_pad_count == 2
    assert c.is_test_point is False
    assert c.is_mounting_hole is False


def test_net_properties():
    net = NetData(code=1, name="GND", pads=[("R1", "1"), ("C1", "2")])
    assert net.pad_count == 2
    assert net.is_single_pin is False
    assert net.is_empty is False

    single_net = NetData(code=2, name="ANT", pads=[("R1", "2")])
    assert single_net.is_single_pin is True


def test_reference_format_validator():
    assert validate_reference_format("R1")[0] is True
    assert validate_reference_format("C12")[0] is True
    assert validate_reference_format("U3")[0] is True
    assert validate_reference_format("TP1")[0] is True

    # Invalid formats
    assert validate_reference_format("")[0] is False
    assert validate_reference_format("R?")[0] is False
    assert validate_reference_format("REF**")[0] is False
    assert validate_reference_format("123")[0] is False


def test_string_sanitizer():
    assert sanitize_string('"Resistor_SMD"') == "Resistor_SMD"
    assert sanitize_string("'GND'") == "GND"
    assert sanitize_string("  C1  ") == "C1"
