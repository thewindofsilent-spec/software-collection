from .base_parser import BaseParser
from .text_parser import TextParser
from .json_parser import JsonParser
from .csv_parser import CsvParser
from .pickle_parser import PickleParser
from .hex_parser import HexParser

ALL_PARSERS = [TextParser, JsonParser, CsvParser, PickleParser, HexParser]
