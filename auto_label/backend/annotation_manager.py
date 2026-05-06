import os
from typing import List, Optional, Dict, Any
from PIL import Image
from ..models.annotation import Annotation, Shape, Point
from .utils import get_json_path


class AnnotationManager:
    def __init__(self):
        self.current_annotation: Optional[Annotation] = None
        self.current_image_path: Optional[str] = None

    def load_annotation(self, image_path: str) -> Optional[Annotation]:
        json_path = get_json_path(image_path)
        if os.path.exists(json_path):
            try:
                self.current_annotation = Annotation.from_json(json_path)
                self.current_image_path = image_path
                return self.current_annotation
            except Exception as e:
                print(f"Error loading annotation: {e}")
                return None
        return None

    def save_annotation(self, annotation: Annotation, image_path: Optional[str] = None) -> bool:
        try:
            target_path = image_path or self.current_image_path
            if not target_path:
                return False

            json_path = get_json_path(target_path)
            annotation.image_path = os.path.basename(target_path)

            with open(json_path, "w", encoding="utf-8") as f:
                f.write(annotation.to_json())

            self.current_annotation = annotation
            self.current_image_path = target_path
            return True
        except Exception as e:
            print(f"Error saving annotation: {e}")
            return False

    def create_empty_annotation(self, image_path: str) -> Annotation:
        try:
            img = Image.open(image_path)
            width, height = img.size
            img.close()
        except:
            width, height = 0, 0

        annotation = Annotation(
            version="5.2.0",
            flags={},
            shapes=[],
            image_path=os.path.basename(image_path),
            image_data=None,
            image_height=height,
            image_width=width,
        )
        self.current_annotation = annotation
        self.current_image_path = image_path
        return annotation

    def add_rectangle(
        self, label: str, x1: float, y1: float, x2: float, y2: float
    ) -> Shape:
        shape = Shape(
            label=label,
            shape_type="rectangle",
            points=[Point(x1, y1), Point(x2, y2)],
        )
        if self.current_annotation:
            self.current_annotation.add_shape(shape)
        return shape

    def add_point(self, label: str, x: float, y: float) -> Shape:
        shape = Shape(
            label=label,
            shape_type="point",
            points=[Point(x, y)],
        )
        if self.current_annotation:
            self.current_annotation.add_shape(shape)
        return shape

    def update_shape(self, index: int, shape: Shape) -> bool:
        if self.current_annotation and 0 <= index < len(self.current_annotation.shapes):
            self.current_annotation.shapes[index] = shape
            return True
        return False

    def remove_shape(self, index: int) -> bool:
        if self.current_annotation:
            self.current_annotation.remove_shape(index)
            return True
        return False

    def clear_shapes(self) -> None:
        if self.current_annotation:
            self.current_annotation.clear_shapes()

    def get_shapes(self) -> List[Shape]:
        if self.current_annotation:
            return self.current_annotation.shapes
        return []

    def get_image_size(self) -> tuple:
        if self.current_annotation:
            return (self.current_annotation.image_width, self.current_annotation.image_height)
        return (0, 0)

    def set_image_size(self, width: int, height: int) -> None:
        if self.current_annotation:
            self.current_annotation.image_width = width
            self.current_annotation.image_height = height
