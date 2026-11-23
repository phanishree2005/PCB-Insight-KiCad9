"""Rules package initialization."""
from pcb_insight.rules.base_rule import BaseRule
from pcb_insight.rules.rule_engine import RuleEngine
from pcb_insight.rules.component_rules import (
    MissingReferenceRule,
    DuplicateReferenceRule,
    MissingValueRule,
    UnassignedFootprintRule,
    PlaceholderReferenceRule,
)
from pcb_insight.rules.connectivity_rules import (
    SinglePinNetRule,
    EmptyNetRule,
    UnassignedElectricalPadRule,
)
from pcb_insight.rules.geometry_rules import (
    MissingBoardOutlineRule,
    UnroutedBoardRule,
)

__all__ = [
    "BaseRule",
    "RuleEngine",
    "MissingReferenceRule",
    "DuplicateReferenceRule",
    "MissingValueRule",
    "UnassignedFootprintRule",
    "PlaceholderReferenceRule",
    "SinglePinNetRule",
    "EmptyNetRule",
    "UnassignedElectricalPadRule",
    "MissingBoardOutlineRule",
    "UnroutedBoardRule",
]
