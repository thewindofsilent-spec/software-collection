import os
import shutil
from typing import List, Optional, Dict
from pathlib import Path
from models.annotation import Annotation
from backend.utils import get_json_path, ensure_dir


class DatasetConverter:
    def __init__(self):
        self.class_names: List[str] = []
        self.class_to_index: Dict[str, int] = {}

    def set_class_names(self, class_names: List[str]) -> None:
        self.class_names = class_names
        self.class_to_index = {name: idx for idx, name in enumerate(class_names)}

    def convert_labelme_to_yolo(
        self,
        image_dir: str,
        output_dir: str,
        class_names: Optional[List[str]] = None,
        copy_images: bool = False,
    ) -> bool:
        try:
            ensure_dir(output_dir)
            labels_dir = os.path.join(output_dir, "labels")
            ensure_dir(labels_dir)

            if copy_images:
                images_dir = os.path.join(output_dir, "images")
                ensure_dir(images_dir)

            if class_names:
                self.set_class_names(class_names)
            elif not self.class_names:
                self._discover_classes(image_dir)

            if not self.class_names:
                print("No classes found!")
                return False

            images = [
                f for f in os.listdir(image_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            for img_file in images:
                img_path = os.path.join(image_dir, img_file)
                json_path = get_json_path(img_path)

                if not os.path.exists(json_path):
                    continue

                try:
                    annotation = Annotation.from_json(json_path)
                    yolo_lines = self._annotation_to_yolo_lines(annotation)

                    label_file = os.path.splitext(img_file)[0] + ".txt"
                    label_path = os.path.join(labels_dir, label_file)

                    with open(label_path, "w") as f:
                        f.write("\n".join(yolo_lines))

                    if copy_images:
                        ext = os.path.splitext(img_file)[1].lower()
                        dest_img = os.path.join(images_dir, os.path.splitext(img_file)[0] + ext)
                        shutil.copy2(img_path, dest_img)

                except Exception as e:
                    print(f"Error converting {img_file}: {e}")
                    continue

            self._create_dataset_yaml(output_dir)
            return True

        except Exception as e:
            print(f"Error in conversion: {e}")
            return False

    def _discover_classes(self, image_dir: str) -> None:
        classes_set = set()
        for img_file in os.listdir(image_dir):
            if not img_file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            json_path = get_json_path(os.path.join(image_dir, img_file))
            if os.path.exists(json_path):
                try:
                    annotation = Annotation.from_json(json_path)
                    for shape in annotation.shapes:
                        if shape.shape_type == "rectangle":
                            classes_set.add(shape.label)
                except:
                    continue

        self.class_names = sorted(list(classes_set))
        self.class_to_index = {name: idx for idx, name in enumerate(self.class_names)}

    def _annotation_to_yolo_lines(self, annotation: Annotation) -> List[str]:
        lines = []
        img_width = annotation.image_width or 1
        img_height = annotation.image_height or 1

        for shape in annotation.shapes:
            if shape.shape_type != "rectangle":
                continue

            if shape.label not in self.class_to_index:
                continue

            class_id = self.class_to_index[shape.label]
            x1, y1 = shape.points[0].x, shape.points[0].y
            x2, y2 = shape.points[1].x, shape.points[1].y

            x_center = (x1 + x2) / 2 / img_width
            y_center = (y1 + y2) / 2 / img_height
            width = abs(x2 - x1) / img_width
            height = abs(y2 - y1) / img_height

            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            width = max(0, min(1, width))
            height = max(0, min(1, height))

            lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        return lines

    def _create_dataset_yaml(self, output_dir: str) -> None:
        yaml_content = f"""# Dataset configuration
path: {output_dir}
train: images
val: images

names:
"""
        for idx, name in enumerate(self.class_names):
            yaml_content += f"  {idx}: {name}\n"

        yaml_path = os.path.join(output_dir, "dataset.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
