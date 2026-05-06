import csv
from typing import Any, Dict
from .base_parser import BaseParser


class CsvParser(BaseParser):
    """Parser for CSV files."""

    name = "CSV Parser"
    extensions = [".csv"]

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            rows = []
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                for row in reader:
                    rows.append(row)
            return {
                "success": True,
                "data": {"headers": headers, "rows": rows, "type": "csv"},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith(".csv")
