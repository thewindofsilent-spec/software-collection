from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseParser(ABC):
    """Abstract base class for data parsers."""

    name: str = "Base Parser"
    extensions: list = []

    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """Parse a file and return structured data.

        Returns:
            Dict with keys:
                - success: bool
                - data: Any (parsed data)
                - error: str (error message if failed)
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
