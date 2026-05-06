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
<<<<<<< HEAD
        self.keypoint_names: List[str] = []
        self.num_keypoints: int = 0
=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55

    def set_class_names(self, class_names: List[str]) -> None:
        self.class_names = class_names
        self.class_to_index = {name: idx for idx, name in enumerate(class_names)}

<<<<<<< HEAD
    def set_keypoint_names(self, keypoint_names: List[str]) -> None:
        self.keypoint_names = keypoint_names
        self.num_keypoints = len(keypoint_names)

=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
    def convert_labelme_to_yolo(
        self,
        image_dir: str,
        output_dir: str,
        class_names: Optional[List[str]] = None,
<<<<<<< HEAD
        keypoint_names: Optional[List[str]] = None,
=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
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

<<<<<<< HEAD
            if keypoint_names:
                self.set_keypoint_names(keypoint_names)
            elif self.num_keypoints == 0:
                self._discover_keypoints(image_dir)

=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
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

<<<<<<< HEAD
    def _discover_keypoints(self, image_dir: str) -> None:
        kp_set = set()
        for img_file in os.listdir(image_dir):
            if not img_file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            json_path = get_json_path(os.path.join(image_dir, img_file))
            if os.path.exists(json_path):
                try:
                    annotation = Annotation.from_json(json_path)
                    for shape in annotation.shapes:
                        if shape.shape_type == "point":
                            try:
                                idx = int(shape.label)
                                kp_set.add(idx)
                            except ValueError:
                                continue
                except:
                    continue

        if kp_set:
            max_idx = max(kp_set) + 1
            self.keypoint_names = [f"kp_{i}" for i in range(max_idx)]
            self.num_keypoints = max_idx

=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
    def _annotation_to_yolo_lines(self, annotation: Annotation) -> List[str]:
        lines = []
        img_width = annotation.image_width or 1
        img_height = annotation.image_height or 1

<<<<<<< HEAD
        # 收集所有点和框，按group_id分组
        rectangles = {}  # group_id -> (class_id, x_center, y_center, width, height)
        keypoints_by_group = {}  # group_id -> [(x, y), ...]

        for shape in annotation.shapes:
            if shape.shape_type == "rectangle":
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

                group_id = shape.group_id if shape.group_id is not None else 0
                rectangles[group_id] = (class_id, x_center, y_center, width, height)
                keypoints_by_group[group_id] = [None] * self.num_keypoints

            elif shape.shape_type == "point":
                group_id = shape.group_id if shape.group_id is not None else 0
                if group_id not in keypoints_by_group:
                    keypoints_by_group[group_id] = [None] * self.num_keypoints
                try:
                    kp_idx = int(shape.label)
                    if 0 <= kp_idx < self.num_keypoints:
                        x, y = shape.points[0].x, shape.points[0].y
                        keypoints_by_group[group_id][kp_idx] = (x / img_width, y / img_height)
                except ValueError:
                    continue

        # 生成YOLO格式行
        for group_id, (class_id, x_center, y_center, width, height) in rectangles.items():
            parts = [f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"]

            if self.num_keypoints > 0 and group_id in keypoints_by_group:
                kps = keypoints_by_group[group_id]
                kp_values = []
                for kp in kps:
                    if kp is not None:
                        kp_values.append(f"{kp[0]:.6f} {kp[1]:.6f} 1")
                    else:
                        kp_values.append("0 0 0")
                parts.append(" ".join(kp_values))
                lines.append(" ".join(parts))
            else:
                lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
=======
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
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55

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

<<<<<<< HEAD
        if self.num_keypoints > 0:
            yaml_content += f"\nkpt_shape: [{self.num_keypoints}, 2]\n"
            if self.keypoint_names:
                yaml_content += "# keypoint names\n"
                for i, name in enumerate(self.keypoint_names):
                    yaml_content += f"# {i}: {name}\n"

=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        yaml_path = os.path.join(output_dir, "dataset.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)
