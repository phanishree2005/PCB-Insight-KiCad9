"""Abstract interface for PCB extraction adapters."""

from abc import ABC, abstractmethod
from typing import Optional
from pcb_insight.core.data_models import BoardData


class BoardAdapter(ABC):
    """Abstract Base Class for extracting BoardData from various sources."""

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the underlying data source or API is currently available."""
        pass

    @abstractmethod
    def extract_board_data(self) -> BoardData:
        """Extracts and normalizes PCB data into a BoardData object."""
        pass

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Returns human-readable name of the adapter."""
        pass
