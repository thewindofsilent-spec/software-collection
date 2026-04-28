import pickle
from typing import Any, Dict
from .base_parser import BaseParser


class PickleParser(BaseParser):
    """Parser for pickle files."""

    name = "Pickle Parser"
    extensions = [".pkl", ".pickle"]

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
            return {
                "success": True,
                "data": {"content": data, "type": "pickle"},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Pickle error: {str(e)}"
            }

    def can_parse(self, file_path: str) -> bool:
        return any(file_path.lower().endswith(ext) for ext in self.extensions)
