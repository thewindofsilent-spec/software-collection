"""
Labelme标注数据转YOLO姿态估计格式脚本

支持矩形框 + 关键点标注

用法：直接修改底部的配置区域
"""

import os
import json
from typing import List, Optional, Tuple


def discover_classes(image_dir: str) -> Tuple[List[str], List[str]]:
    """自动发现类别和关键点名称"""
    classes_set = set()
    keypoints_set = set()

    for img_file in os.listdir(image_dir):
        if not img_file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        json_path = get_json_path(os.path.join(image_dir, img_file))
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for shape in data.get("shapes", []):
                    if shape.get("shape_type") == "rectangle":
                        classes_set.add(shape.get("label", ""))
                    elif shape.get("shape_type") == "point":
                        keypoints_set.add(shape.get("label", ""))
            except Exception:
                continue

    # 类别按字母排序，关键点按数字排序
    classes = sorted(list(classes_set))
    keypoints = sorted(list(keypoints_set), key=lambda x: int(x) if x.isdigit() else x)

    return classes, keypoints


def get_json_path(img_path: str) -> str:
    """获取标注JSON文件路径"""
    return os.path.splitext(img_path)[0] + ".json"


def convert_rect_to_yolo_bbox(
    points: List[List[float]],
    img_width: int,
    img_height: int
) -> Tuple[float, float, float, float]:
    """将矩形坐标转换为YOLO格式 (x_center, y_center, width, height) 归一化到0-1"""
    x1, y1 = points[0]
    x2, y2 = points[1]

    x_center = (x1 + x2) / 2 / img_width
    y_center = (y1 + y2) / 2 / img_height
    width = abs(x2 - x1) / img_width
    height = abs(y2 - y1) / img_height

    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    width = max(0.0, min(1.0, width))
    height = max(0.0, min(1.0, height))

    return x_center, y_center, width, height


def convert_point_to_yolo(
    point: List[float],
    img_width: int,
    img_height: int,
    visible: int = 2
) -> Tuple[float, float, int]:
    """将点转换为YOLO格式 (x, y, visible)"""
    x = point[0] / img_width
    y = point[1] / img_height
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    return x, y, visible


def create_dataset_yaml(output_dir: str, class_names: List[str], keypoint_names: List[str]) -> None:
    """创建YOLO姿态估计数据集配置文件"""
    yaml_content = f"""# YOLO Pose Dataset configuration
# 自动生成

path: {os.path.abspath(output_dir)}
train: images
val: images

kpt_shape: [{len(keypoint_names)}, 3]  # 关键点数量，每个关键点3个值(x, y, visible)
flip_idx: []

# 类别
names:
"""
    for idx, name in enumerate(class_names):
        yaml_content += f"  {idx}: {name}\n"

    yaml_path = os.path.join(output_dir, "dataset.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"已创建数据集配置: {yaml_path}")


def labelme_to_yolo_pose(
    input_dir: str,
    output_dir: str,
    class_names: Optional[List[str]] = None,
    keypoint_names: Optional[List[str]] = None,
    copy_images: bool = False
) -> bool:
    """
    将Labelme标注转换为YOLO姿态估计格式

    Args:
        input_dir: 包含图像和JSON标注文件的目录
        output_dir: 输出目录
        class_names: 类别列表，None时自动发现
        keypoint_names: 关键点名称列表，None时自动发现
        copy_images: 是否复制图像到输出目录

    Returns:
        是否转换成功
    """
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录不存在 - {input_dir}")
        return False

    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(labels_dir, exist_ok=True)

    images_dir = None
    if copy_images:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

    # 获取或发现类别和关键点
    if class_names is None or keypoint_names is None:
        print("正在自动发现类别和关键点...")
        discovered_classes, discovered_keypoints = discover_classes(input_dir)
        class_names = class_names or discovered_classes
        keypoint_names = keypoint_names or discovered_keypoints

    if not class_names:
        print("错误: 未找到任何类别")
        return False

    if not keypoint_names:
        print("警告: 未找到关键点，将只转换边界框")

    print(f"类别列表: {class_names}")
    print(f"关键点列表: {keypoint_names}")

    class_to_index = {name: idx for idx, name in enumerate(class_names)}
    keypoint_to_index = {name: idx for idx, name in enumerate(keypoint_names)}

    # 获取所有图像
    image_extensions = (".jpg", ".jpeg", ".png", ".bmp")
    images = [f for f in os.listdir(input_dir) if f.lower().endswith(image_extensions)]

    if not images:
        print("错误: 目录中未找到图像文件")
        return False

    print(f"找到 {len(images)} 张图像")

    converted = 0
    skipped = 0

    for img_file in images:
        img_path = os.path.join(input_dir, img_file)
        json_path = get_json_path(img_path)

        if not os.path.exists(json_path):
            skipped += 1
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            img_width = data.get("imageWidth", 1)
            img_height = data.get("imageHeight", 1)

            # 分离矩形框和关键点
            rectangles = []
            points = []

            for shape in data.get("shapes", []):
                if shape.get("shape_type") == "rectangle":
                    label = shape.get("label", "")
                    if label in class_to_index:
                        rectangles.append(shape)
                elif shape.get("shape_type") == "point":
                    label = shape.get("label", "")
                    if label in keypoint_to_index:
                        points.append(shape)

            if not rectangles:
                skipped += 1
                continue

            # 为每个矩形框生成YOLO姿态行
            yolo_lines = []

            for rect in rectangles:
                label = rect.get("label", "")
                class_id = class_to_index[label]
                bbox_points = rect.get("points", [])

                if len(bbox_points) != 2:
                    continue

                x_center, y_center, width, height = convert_rect_to_yolo_bbox(bbox_points, img_width, img_height)

                # 初始化关键点数组
                num_keypoints = len(keypoint_names)
                keypoint_data = [0.0] * (num_keypoints * 3)  # x1, y1, v1, x2, y2, v2, ...

                # 填充关键点
                for point_shape in points:
                    point_label = point_shape.get("label", "")
                    if point_label in keypoint_to_index:
                        kp_idx = keypoint_to_index[point_label]
                        kp_point = point_shape.get("points", [])[0]
                        kx, ky, kv = convert_point_to_yolo(kp_point, img_width, img_height)
                        keypoint_data[kp_idx * 3] = kx
                        keypoint_data[kp_idx * 3 + 1] = ky
                        keypoint_data[kp_idx * 3 + 2] = kv

                # 构建YOLO姿态行 (不包含num_keypoints)
                if num_keypoints > 0:
                    kp_str = " ".join([f"{v:.6f}" for v in keypoint_data])
                    yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f} {kp_str}"
                else:
                    yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"

                yolo_lines.append(yolo_line)

            # 保存标签文件
            if yolo_lines:
                label_file = os.path.splitext(img_file)[0] + ".txt"
                label_path = os.path.join(labels_dir, label_file)
                with open(label_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(yolo_lines))

                if copy_images and images_dir:
                    ext = os.path.splitext(img_file)[1].lower()
                    dest_img = os.path.join(images_dir, os.path.splitext(img_file)[0] + ext)
                    import shutil
                    shutil.copy2(img_path, dest_img)

                converted += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"处理 {img_file} 时出错: {e}")
            skipped += 1
            continue

    print(f"\n转换完成: {converted} 张图像已转换, {skipped} 张跳过")

    if converted > 0:
        create_dataset_yaml(output_dir, class_names, keypoint_names)
        print(f"\n输出目录: {os.path.abspath(output_dir)}")
        print(f"  labels/ - YOLO姿态标注文件")
        if copy_images:
            print(f"  images/ - 图像文件副本")
        print(f"  dataset.yaml - 数据集配置")

    return converted > 0


def main():
    # ==================== 配置区域 ====================
    INPUT_DIR = r"C:\Users\admin\Desktop\label\test\label"          # 包含图像和JSON标注文件的目录
    OUTPUT_DIR = r"C:\Users\admin\Desktop\label\test\result"        # YOLO格式输出目录
    COPY_IMAGES = True                                               # 是否复制图像到输出目录
    # ===============================================

    # 类别和关键点名称，None表示自动从JSON中发现
    CLASS_NAMES = None        # 如 ["mouse"]，None=自动发现
    KEYPOINT_NAMES = None     # 如 ["0", "1", "2"]，None=自动发现

    labelme_to_yolo_pose(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        class_names=CLASS_NAMES,
        keypoint_names=KEYPOINT_NAMES,
        copy_images=COPY_IMAGES
    )


if __name__ == "__main__":
    main()
