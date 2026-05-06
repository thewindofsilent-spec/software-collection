import json
from typing import Any, Dict
from .base_parser import BaseParser


class JsonParser(BaseParser):
    """Parser for JSON files."""

    name = "JSON Parser"
    extensions = [".json"]

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "success": True,
                "data": {"content": data, "type": "json"},
                "error": None
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "data": None,
                "error": f"JSON decode error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".json")
