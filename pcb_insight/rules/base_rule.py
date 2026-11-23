"""Base class and interface for PCB Insight analysis rules."""

from abc import ABC, abstractmethod
from typing import List, Optional

from pcb_insight.analyzers.component_analyzer import ComponentAnalysisReport
from pcb_insight.analyzers.connectivity_analyzer import ConnectivityAnalysisReport
from pcb_insight.core.data_models import AnalysisFinding, BoardData, FindingSeverity


class BaseRule(ABC):
    """Abstract Base Class for an individual explainable PCB design check."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique alphanumeric rule identifier, e.g. 'RULE-COMP-001'."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable rule title."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed engineering description of what the rule checks."""
        pass

    @property
    @abstractmethod
    def severity(self) -> FindingSeverity:
        """Default severity classification for violations of this rule."""
        pass

    @abstractmethod
    def evaluate(
        self,
        board: BoardData,
        comp_report: ComponentAnalysisReport,
        conn_report: ConnectivityAnalysisReport,
    ) -> List[AnalysisFinding]:
        """Evaluates the rule against board data and returns findings."""
        pass
