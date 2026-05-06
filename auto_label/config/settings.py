import os

APP_NAME = "AutoLabel"
APP_VERSION = "1.0.0"

DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
DEFAULT_EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

LABELME_VERSION = "5.2.0"

YOLO_DEFAULTS = {
    "epochs": 100,
    "batch": 16,
    "imgsz": 640,
    "workers": 8,
    "patience": 50,
    "device": "0",
    "project": "runs/detect",
    "name": "train",
}

AUTO_LABEL_DEFAULTS = {
    "conf": 0.25,
    "iou": 0.45,
    "max_det": 300,
}
