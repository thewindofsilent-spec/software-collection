from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import json


@dataclass
class Point:
    x: float
    y: float

    def to_list(self) -> List[float]:
        return [self.x, self.y]

    @classmethod
    def from_list(cls, data: List[float]) -> "Point":
        return cls(x=data[0], y=data[1])


@dataclass
class Shape:
    label: str
    shape_type: str  # "rectangle" or "point"
    points: List[Point] = field(default_factory=list)
    group_id: Optional[int] = None
    description: str = ""
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "points": [p.to_list() for p in self.points],
            "group_id": self.group_id,
            "description": self.description,
            "shape_type": self.shape_type,
            "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shape":
        points = [Point.from_list(p) for p in data.get("points", [])]
        return cls(
            label=data.get("label", ""),
            shape_type=data.get("shape_type", "rectangle"),
            points=points,
            group_id=data.get("group_id"),
            description=data.get("description", ""),
            flags=data.get("flags", {}),
        )


@dataclass
class Annotation:
    version: str = "5.2.0"
    flags: Dict[str, Any] = field(default_factory=dict)
    shapes: List[Shape] = field(default_factory=list)
    image_path: str = ""
    image_data: Optional[str] = None
    image_height: int = 0
    image_width: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "flags": self.flags,
            "shapes": [s.to_dict() for s in self.shapes],
            "imagePath": self.image_path,
            "imageData": self.image_data,
            "imageHeight": self.image_height,
            "imageWidth": self.image_width,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Annotation":
        shapes = [Shape.from_dict(s) for s in data.get("shapes", [])]
        return cls(
            version=data.get("version", "5.2.0"),
            flags=data.get("flags", {}),
            shapes=shapes,
            image_path=data.get("imagePath", ""),
            image_data=data.get("imageData"),
            image_height=data.get("imageHeight", 0),
            image_width=data.get("imageWidth", 0),
        )

    def to_json(self, filepath: Optional[str] = None) -> str:
        json_str = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    @classmethod
    def from_json(cls, filepath: str) -> "Annotation":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_rectangles(self) -> List[Shape]:
        return [s for s in self.shapes if s.shape_type == "rectangle"]

    def get_points(self) -> List[Shape]:
        return [s for s in self.shapes if s.shape_type == "point"]

    def add_shape(self, shape: Shape) -> None:
        self.shapes.append(shape)

    def remove_shape(self, index: int) -> None:
        if 0 <= index < len(self.shapes):
            self.shapes.pop(index)

    def clear_shapes(self) -> None:
        self.shapes.clear()
