# Data Reader - PySide6 MVC 数据读取器

基于 PySide6 开发的文件数据读取器，采用 MVC（Model-View-Controller）架构。

## 功能特性

- **多格式支持**: 文本、JSON、CSV、Pickle 文件读取，以及二进制数据的十六进制显示
- **自动检测**: 根据文件扩展名自动选择合适的解析器
- **手动选择**: 通过下拉框手动切换解析方式
- **拖拽支持**: 支持将文件直接拖入窗口打开
- **十六进制回退**: 无法解析的文件以十六进制格式显示
- **可扩展**: 易于添加新的解析器

## 项目结构

```
data_reader/
├── main.py                 # 应用入口
├── models/
│   └── data_model.py       # Model层 - 数据和解析器管理
├── views/
│   └── main_window.py      # View层 - UI组件
├── controllers/
│   └── data_controller.py  # Controller层 - 业务逻辑
└── parsers/
    ├── __init__.py
    ├── base_parser.py      # 解析器抽象基类
    ├── text_parser.py      # 文本/UTF-8文件解析器
    ├── json_parser.py      # JSON文件解析器
    ├── csv_parser.py       # CSV文件解析器
    ├── pickle_parser.py    # Python pickle文件解析器
    └── hex_parser.py       # 二进制/十六进制显示解析器
```

## MVC 各层职责

| 层级 | 职责 |
|------|------|
| **Model** | 数据管理、解析器选择、文件处理 |
| **View** | UI渲染、用户输入采集、数据展示 |
| **Controller** | 业务逻辑、连接 Model 和 View |

## 支持的格式

| 解析器 | 扩展名 | 显示方式 |
|--------|--------|----------|
| Text Parser | .txt, .log, .py, .md, .csv, .json, .xml, .html | 按行显示 |
| JSON Parser | .json | 格式化缩进显示 |
| CSV Parser | .csv | 逗号分隔显示 |
| Pickle Parser | .pkl, .pickle | 格式化显示（dict/list会美化） |
| Hex Viewer | 其他所有格式 | 十六进制转储 + ASCII |

## 使用方法

```bash
cd data_reader
pip install PySide6
python main.py
```

1. 点击 **Open File** 按钮选择数据文件，或直接拖拽文件到窗口
2. 程序自动检测文件格式并显示数据
3. 通过 **Parser** 下拉框可手动切换解析方式

## 添加新的解析器

1. 在 `parsers/` 目录下创建新的解析器类，继承 `BaseParser`
2. 实现 `parse()` 和 `can_parse()` 方法
3. 在 `parsers/__init__.py` 中添加新的解析器类
4. 重启应用

示例：

```python
from parsers import BaseParser

class MyParser(BaseParser):
    name = "My Parser"
    extensions = [".myext"]

    def parse(self, file_path):
        # 解析逻辑
        return {"success": True, "data": {...}, "error": None}

    def can_parse(self, file_path):
        return file_path.endswith(".myext")
```
