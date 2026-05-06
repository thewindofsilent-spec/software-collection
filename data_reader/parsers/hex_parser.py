from typing import Any, Dict
from .base_parser import BaseParser


class HexParser(BaseParser):
    """Parser for displaying binary/unknown data as hex."""

    name = "Hex Viewer"
    extensions = []

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()

            hex_lines = []
            for i in range(0, len(raw_data), 16):
                chunk = raw_data[i:i+16]
                hex_part = " ".join(f"{b:02x}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                hex_lines.append(f"{i:08x}  {hex_part:<48}  {ascii_part}")

            return {
                "success": True,
                "data": {"lines": hex_lines, "raw_size": len(raw_data), "type": "hex"},
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def can_parse(self, file_path: str) -> bool:
        return True
