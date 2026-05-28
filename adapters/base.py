from abc import ABC, abstractmethod
from typing import Any
from core.blueprint import Blueprint


class AdapterError(Exception):
    """Base exception class for all spreadsheet adapter errors."""
    pass


class AbstractAdapter(ABC):
    @abstractmethod
    def render(self, blueprint: Blueprint, spreadsheet_handle: Any = None) -> None:
        """
        Renders the blueprint on the target spreadsheet instance.
        """
        pass
