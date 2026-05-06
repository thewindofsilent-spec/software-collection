# Video to Picture

AVI video frame extraction tool.

## Requirements

```bash
pip install opencv-python PySide6
```

## GUI Version

```bash
python main.py
```

Features:
- Drag and drop video files
- Adjustable frame interval
- Start/end frame selection
- Multiple image formats (PNG, JPEG, BMP)
- Progress bar with extraction log

## Command Line Version

```bash
python extract_frames.py video.avi output_folder --interval 30
```

Options:
- `--interval FRAMES` - Extract every N frames (default: 30)
- `--start FRAME` - Start from frame N (default: 0)
- `--end FRAME` - End at frame N (0 = end of video)
- `--format FORMAT` - Image format: png, jpg, bmp (default: png)

Examples:
```bash
python extract_frames.py video.avi
python extract_frames.py video.avi ./frames --interval 10
python extract_frames.py video.avi ./output --start 100 --end 500 --format jpg
```