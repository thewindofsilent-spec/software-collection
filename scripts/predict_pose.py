"""
YOLO姿态估计模型预测脚本

将预测结果保存为LabelMe JSON格式

用法：直接修改底部的配置区域
"""

import os
import json
from typing import List, Dict, Tuple
from ultralytics import YOLO


def create_labelme_json(
    image_path: str,
    image_width: int,
    image_height: int,
    boxes: List[Dict],
    keypoints: List[Dict],
    version: str = "5.2.0"
) -> Dict:
    """
    创建LabelMe格式的JSON字典

    Args:
        image_path: 图像文件名
        image_width: 图像宽度
        image_height: 图像高度
        boxes: 边界框列表 [{"label": str, "points": [[x1,y1], [x2,y2]]}]
        keypoints: 关键点列表 [{"label": str, "points": [[x,y]]}]
        version: LabelMe版本

    Returns:
        LabelMe格式的字典
    """
    shapes = []

    # 添加边界框
    for box in boxes:
        shapes.append({
            "label": box["label"],
            "points": box["points"],
            "group_id": None,
            "description": "",
            "shape_type": "rectangle",
            "flags": {}
        })

    # 添加关键点
    for kp in keypoints:
        shapes.append({
            "label": kp["label"],
            "points": kp["points"],
            "group_id": None,
            "description": "",
            "shape_type": "point",
            "flags": {}
        })

    return {
        "version": version,
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width
    }


def yolo_to_labelme_boxes(
    yolo_box: Tuple[float, float, float, float],
    img_width: int,
    img_height: int,
    class_id: int,
    class_names: Dict[int, str]
) -> Dict:
    """将YOLO bbox转换为LabelMe格式的矩形"""
    x_center, y_center, width, height = yolo_box

    # YOLO中心坐标转角点坐标
    x1 = (x_center - width / 2) * img_width
    y1 = (y_center - height / 2) * img_height
    x2 = (x_center + width / 2) * img_width
    y2 = (y_center + height / 2) * img_height

    return {
        "label": class_names.get(class_id, str(class_id)),
        "points": [[float(x1), float(y1)], [float(x2), float(y2)]]
    }


def yolo_keypoints_to_labelme(
    yolo_kps: List[float],
    num_keypoints: int,
    img_width: int,
    img_height: int,
    kp_names: Dict[int, str]
) -> List[Dict]:
    """将YOLO关键点转换为LabelMe格式的点"""
    result = []
    for i in range(num_keypoints):
        x = yolo_kps[i * 3] * img_width
        y = yolo_kps[i * 3 + 1] * img_height
        # v = yolo_kps[i * 3 + 2]  # 可见性，不用于labelme

        result.append({
            "label": kp_names.get(i, str(i)),
            "points": [[x, y]]
        })
    return result


def predict_and_save(
    model_path: str,
    image_dir: str,
    output_dir: str,
    conf: float = 0.25,
    iou: float = 0.45,
    max_det: int = 100,
    save_images: bool = True,
    save_labels: bool = True
) -> bool:
    """
    使用YOLO模型预测并保存为LabelMe JSON格式

    Args:
        model_path: 模型路径
        image_dir: 输入图像目录
        output_dir: 输出目录
        conf: 置信度阈值
        iou: IOU阈值
        max_det: 最大检测数
        save_images: 是否保存带标注的图像
        save_labels: 是否保存LabelMe JSON

    Returns:
        是否成功
    """
    if not os.path.exists(model_path):
        print(f"错误: 模型文件不存在 - {model_path}")
        return False

    if not os.path.exists(image_dir):
        print(f"错误: 图像目录不存在 - {image_dir}")
        return False

    # 加载模型
    print(f"加载模型: {model_path}")
    model = YOLO(model_path)

    # 获取类别信息
    # 从模型中获取类别名称（如果有）
    names = model.names if hasattr(model, 'names') else {0: "object"}
    kp_names = {i: str(i) for i in range(17)}  # 默认17个关键点

    # 获取数据集配置中的关键点数量（如果有）
    num_keypoints = 3  # 默认值，可根据模型调整

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(labels_dir, exist_ok=True)

    if save_images:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

    # 获取所有图像
    image_extensions = (".jpg", ".jpeg", ".png", ".bmp")
    images = [f for f in os.listdir(image_dir) if f.lower().endswith(image_extensions)]

    if not images:
        print(f"错误: 目录中未找到图像 - {image_dir}")
        return False

    print(f"找到 {len(images)} 张图像")

    # 预测
    from PIL import Image
    predicted = 0
    no_detection = 0

    for img_file in images:
        img_path = os.path.join(image_dir, img_file)

        # 获取图像尺寸
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        # 执行预测
        results = model.predict(
            source=img_path,
            conf=conf,
            iou=iou,
            max_det=max_det,
            verbose=False
        )

        # 提取预测结果
        boxes = []
        keypoints = []

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            # 处理每个检测到的对象
            for box, kp in zip(result.boxes, result.keypoints):
                # 边界框
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls_id = int(box.cls[0].cpu().numpy())

                # 转换为归一化的YOLO格式 (x_center, y_center, width, height)
                x_center = ((x1 + x2) / 2) / img_width
                y_center = ((y1 + y2) / 2) / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height

                # 添加边界框
                boxes.append(yolo_to_labelme_boxes(
                    (x_center, y_center, width, height),
                    img_width, img_height, cls_id, names
                ))

                # 处理关键点
                if kp is not None:
                    # kp.data shape: [num_detections, num_keypoints, 3]
                    kp_tensor = kp.data  # Shape: [N, K, 3] where N=detections, K=keypoints
                    if len(kp_tensor) > 0:
                        # 获取该检测的关键点 (取第一个检测)
                        det_kps = kp_tensor[0].cpu().numpy()  # Shape: [K, 3]
                        for i in range(len(det_kps)):
                            # YOLO返回的关键点已经是绝对像素坐标
                            x = float(det_kps[i][0])
                            y = float(det_kps[i][1])
                            keypoints.append({
                                "label": kp_names.get(i, str(i)),
                                "points": [[float(x), float(y)]]
                            })

        # 保存LabelMe JSON
        if save_labels:
            label_file = os.path.splitext(img_file)[0] + ".json"
            label_path = os.path.join(labels_dir, label_file)

            labelme_data = create_labelme_json(
                image_path=img_file,
                image_width=img_width,
                image_height=img_height,
                boxes=boxes,
                keypoints=keypoints
            )

            with open(label_path, "w", encoding="utf-8") as f:
                json.dump(labelme_data, f, indent=2, ensure_ascii=False)

        # 保存带标注的图像
        if save_images and boxes:
            result_plot = results[0].plot()
            result_img = Image.fromarray(result_plot)
            output_img_path = os.path.join(images_dir, img_file)
            result_img.save(output_img_path)
            predicted += 1
        elif not boxes:
            no_detection += 1

    print(f"\n预测完成:")
    print(f"  有检测结果: {predicted} 张")
    print(f"  无检测结果: {no_detection} 张")
    print(f"  输出目录: {os.path.abspath(output_dir)}")

    if save_labels:
        print(f"  labels/ - LabelMe JSON文件")
    if save_images:
        print(f"  images/ - 可视化图像")

    return True


def main():
    # ==================== 配置区域 ====================
    # 模型路径
    MODEL_PATH = r"C:\Users\admin\Desktop\label\unknown\best.pt"

    # 输入图像目录
    IMAGE_DIR = r"C:\Users\admin\Desktop\label\test\aa"

    # 输出目录
    OUTPUT_DIR = r"C:\Users\admin\Desktop\label\test\aa"

    # 预测参数d
    CONF = 0.25                      # 置信度阈值
    IOU = 0.45                       # IOU阈值
    MAX_DET = 100                    # 最大检测数

    # 保存选项
    SAVE_IMAGES = True               # 保存带标注的可视化图像
    SAVE_LABELS = True               # 保存LabelMe JSON格式
    # ===============================================

    predict_and_save(
        model_path=MODEL_PATH,
        image_dir=IMAGE_DIR,
        output_dir=OUTPUT_DIR,
        conf=CONF,
        iou=IOU,
        max_det=MAX_DET,
        save_images=SAVE_IMAGES,
        save_labels=SAVE_LABELS
    )


if __name__ == "__main__":
    main()
