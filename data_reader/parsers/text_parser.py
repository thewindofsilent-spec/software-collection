from typing import Any, Dict
from .base_parser import BaseParser


class TextParser(BaseParser):
    """Parser for plain text files (UTF-8)."""

    name = "Text Parser"
    extensions = [".txt", ".log", ".py", ".md", ".csv", ".json", ".xml", ".html", ".htm"]

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return {
                "success": True,
                "data": {"lines": lines, "type": "text"},
                "error": None
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "data": None,
                "error": "Unable to decode as UTF-8 text"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def can_parse(self, file_path: str) -> bool:
        return any(file_path.lower().endswith(ext) for ext in self.extensions)
