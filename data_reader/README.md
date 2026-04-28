# Data Reader - PySide6 MVC Application

A data file reader application built with PySide6 following the MVC (Model-View-Controller) architecture.

## Features

- **Multi-format support**: Text, JSON, CSV, Pickle, and binary hex display
- **Auto-detection**: Automatically detects the appropriate parser based on file extension
- **Manual selection**: Choose parsing method manually via dropdown
- **Hex fallback**: Binary or unrecognized files display as hex dump
- **Extensible**: Easy to add new parsers

## Architecture

```
data_reader/
├── main.py                 # Application entry point
├── models/
│   └── data_model.py       # Model layer - data and parser management
├── views/
│   └── main_window.py     # View layer - UI components
├── controllers/
│   └── data_controller.py  # Controller layer - business logic
└── parsers/
    ├── __init__.py
    ├── base_parser.py      # Abstract base parser
    ├── text_parser.py      # Text/UTF-8 files
    ├── json_parser.py      # JSON files
    ├── csv_parser.py       # CSV files
    ├── pickle_parser.py    # Python pickle files
    └── hex_parser.py       # Binary/hex view
```

## MVC Components

| Layer | Responsibility |
|-------|----------------|
| **Model** | Data management, parser selection, file handling |
| **View** | UI rendering, user input collection, data display |
| **Controller** | Business logic, coordinates Model and View |

## Supported Formats

| Parser | Extensions | Display |
|--------|------------|---------|
| Text Parser | .txt, .log, .py, .md, .csv, .json, .xml, .html | Line-by-line table |
| JSON Parser | .json | Key-value table |
| CSV Parser | .csv | Tabular grid |
| Pickle Parser | .pkl, .pickle | Type and value |
| Hex Viewer | (all others) | Hex dump with ASCII |

## Usage

```bash
cd data_reader
python main.py
```

1. Click **Open File** to select a data file
2. The app auto-detects the format and displays data
3. Use the **Parser** dropdown to switch parsing methods manually

## Adding New Parsers

1. Create a new parser class inheriting from `BaseParser` in `parsers/`
2. Implement `parse()` and `can_parse()` methods
3. Add the parser class to `parsers/__init__.py`
4. Restart the application

Example:

```python
from parsers import BaseParser

class MyParser(BaseParser):
    name = "My Parser"
    extensions = [".myext"]

    def parse(self, file_path):
        # Your parsing logic
        return {"success": True, "data": {...}, "error": None}

    def can_parse(self, file_path):
        return file_path.endswith(".myext")
```
