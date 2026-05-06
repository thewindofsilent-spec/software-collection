from typing import Any, Dict, List, Optional
from parsers import ALL_PARSERS, BaseParser


class DataModel:
    """Model layer - handles data and parser management."""

    def __init__(self):
        self._current_file: Optional[str] = None
        self._current_data: Optional[Dict[str, Any]] = None
        self._parsers: List[BaseParser] = [p() for p in ALL_PARSERS]
        self._current_parser: Optional[BaseParser] = None

    def set_file(self, file_path: str) -> bool:
        self._current_file = file_path
        return True

    def get_current_file(self) -> Optional[str]:
        return self._current_file

    def get_parsers(self) -> List[BaseParser]:
        return self._parsers

    def get_parser_names(self) -> List[str]:
        return [p.name for p in self._parsers]

    def set_parser(self, parser_name: str) -> bool:
        for parser in self._parsers:
            if parser.name == parser_name:
                self._current_parser = parser
                return True
        return False

    def get_current_parser(self) -> Optional[BaseParser]:
        return self._current_parser

    def auto_detect_parser(self) -> Optional[BaseParser]:
        if not self._current_file:
            return None
        for parser in self._parsers:
            if parser.can_parse(self._current_file) and parser.name != "Hex Viewer":
                return parser
        return self._parsers[-1]

    def parse_file(self, parser: Optional[BaseParser] = None) -> Dict[str, Any]:
        if not self._current_file:
            return {"success": False, "data": None, "error": "No file selected"}

        parser = parser or self._current_parser or self.auto_detect_parser()
        if parser:
            return parser.parse(self._current_file)
        return {"success": False, "data": None, "error": "No suitable parser found"}
