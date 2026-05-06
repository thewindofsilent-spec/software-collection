import os
from typing import List, Tuple, Optional
from pathlib import Path


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def get_name_without_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]


def list_images_in_directory(directory: str, recursive: bool = True) -> List[str]:
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    images = []

    if recursive:
        for root, _, files in os.walk(directory):
            for f in files:
                if get_file_extension(f) in image_extensions:
                    images.append(os.path.join(root, f))
    else:
        for f in os.listdir(directory):
            path = os.path.join(directory, f)
            if os.path.isfile(path) and get_file_extension(f) in image_extensions:
                images.append(path)

    return sorted(images)


def get_json_path(image_path: str) -> str:
    return os.path.splitext(image_path)[0] + ".json"


def ensure_dir(directory: str) -> None:
    Path(directory).mkdir(parents=True, exist_ok=True)


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
