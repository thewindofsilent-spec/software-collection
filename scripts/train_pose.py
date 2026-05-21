"""
YOLOv8 姿态估计模型再训练脚本

用法：直接修改底部的配置区域
"""

import os
import torch
from ultralytics import YOLO


def get_optimal_batch_size(imgsz: int = 640, device: str = "0") -> int:
    """
    根据GPU显存自动选择合适的批次大小

    Args:
        imgsz: 输入图像尺寸
        device: 设备ID ("0", "1", "cpu")

    Returns:
        推荐的批次大小
    """
    if device == "cpu" or not torch.cuda.is_available():
        return 4  # CPU模式默认batch=4

    # GPU模式，根据显存估算
    try:
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
    except:
        gpu_mem = 8  # 默认值

    # 根据图像尺寸调整系数 (尺寸越大，batch越小)
    size_factor = (640 / imgsz) ** 2
    gpu_mem *= size_factor

    # 不同显存的推荐batch
    if gpu_mem >= 16:
        return 16
    elif gpu_mem >= 12:
        return 12
    elif gpu_mem >= 8:
        return 8
    elif gpu_mem >= 6:
        return 4
    elif gpu_mem >= 4:
        return 2
    else:
        return 1


def get_optimal_workers() -> int:
    """
    根据CPU核心数自动选择数据加载线程数

    Returns:
        推荐的工作线程数
    """
    cpu_count = os.cpu_count() or 1

    # 数据加载线程数一般为CPU核心数的50%-75%
    workers = max(1, int(cpu_count * 0.5))

    # 限制在合理范围
    if cpu_count <= 2:
        return 1
    elif cpu_count <= 4:
        return 2
    elif cpu_count <= 8:
        return 4
    else:
        return min(workers, 8)


def auto_detect_device() -> str:
    """
    自动检测可用设备

    Returns:
        设备字符串 ("0", "1", "cpu")
    """
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        if gpu_count > 1:
            return "0"  # 默认使用第一个GPU
        return "0"
    return "cpu"


def train_yolo_pose(
    model: str,
    data_yaml: str,
    epochs: int = 100,
    batch: int = 16,
    imgsz: int = 640,
    workers: int = 8,
    patience: int = 50,
    project: str = None,
    name: str = "train",
    device: str = "0",
    resume: bool = False,
    pretrained: bool = True,
    optimizer: str = "auto",
    lr0: float = 0.01,
    lrf: float = 0.01,
    momentum: float = 0.937,
    weight_decay: float = 0.0005,
    warmup_epochs: float = 3.0,
    warmup_momentum: float = 0.8,
    warmup_bias_lr: float = 0.1,
    close_mosaic: int = 10,
    amp: bool = True,
    fraction: float = 1.0,
):
    """
    训练 YOLO 姿态估计模型

    Args:
        model: 预训练模型路径或模型名称 (如 yolov8s-pose.pt)
        data_yaml: 数据集配置文件路径
        epochs: 训练轮数
        batch: 批次大小
        imgsz: 输入图像尺寸
        workers: 数据加载线程数
        patience: 早停耐心值
        project: 项目保存目录 (默认为 model 同目录下的 train_results)
        name: 实验名称
        device: 训练设备 (0=GPU0, cpu=CPU)
        resume: 是否从上次中断处继续训练
        pretrained: 是否使用预训练权重
        optimizer: 优化器 (SGD, Adam, AdamW, auto)
        lr0: 初始学习率
        lrf: 最终学习率 (LR0 * LRF)
        momentum: SGD 动量
        weight_decay: 权重衰减
        warmup_epochs: 预热轮数
        close_mosaic: 在最后N轮禁用马赛克增强
        amp: 是否使用混合精度训练
        fraction: 使用数据集的比例
    """
    # 如果未指定 project，使用 model 同目录下的 train_results
    if project is None:
        model_dir = os.path.dirname(os.path.abspath(model))
        project = os.path.join(model_dir, "train_results")

    # 加载模型
    print(f"加载模型: {model}")
    yolo_model = YOLO(model)

    # 训练参数
    args = {
        "data": data_yaml,
        "epochs": epochs,
        "batch": batch,
        "imgsz": imgsz,
        "workers": workers,
        "patience": patience,
        "project": project,
        "name": name,
        "device": device,
        "resume": resume,
        "pretrained": pretrained,
        "optimizer": optimizer,
        "lr0": lr0,
        "lrf": lrf,
        "momentum": momentum,
        "weight_decay": weight_decay,
        "warmup_epochs": warmup_epochs,
        "warmup_momentum": warmup_momentum,
        "warmup_bias_lr": warmup_bias_lr,
        "close_mosaic": close_mosaic,
        "amp": amp,
        "fraction": fraction,
    }

    # 打印训练配置
    print("=" * 50)
    print("训练配置:")
    print("=" * 50)
    for k, v in args.items():
        print(f"  {k}: {v}")
    print("=" * 50)

    # 开始训练
    results = yolo_model.train(**args)

    # 打印最佳模型路径
    print(f"\n训练完成!")
    print(f"最佳模型: {results.save_dir / 'weights' / 'best.pt'}")
    print(f"最后模型: {results.save_dir / 'weights' / 'last.pt'}")

    return results


def main():
    # ==================== 配置区域 ====================
    # 预训练模型 (可从 https://github.com/ultralytics/assets/releases 下载)
    MODEL = r"C:\Users\admin\Desktop\label\test\yolo26s-pose.pt"      # 或指定本地路径如 yolov8s-pose.pt

    # 数据集配置文件 (dataset.yaml 路径)
    DATA_YAML = r"C:\Users\admin\Desktop\label\test\result\dataset.yaml"

    # 训练参数
    EPOCHS = 100                      # 训练轮数
    IMGSZ = 640                       # 输入图像尺寸 (自动调整batch)
    PATIENCE = 10                     # 早停耐心值
    # PROJECT = None,                 # 默认为 model 同目录下的 train_results
    NAME = "train"                   # 实验名称

    # 自动选择最佳参数 (-1 表示自动适配显存)
    BATCH = -1
    WORKERS = get_optimal_workers()

    # 设备 (0=GPU0, 1=GPU1, cpu=CPU)
    DEVICE = "0"

    # 优化器参数
    OPTIMIZER = "auto"               # auto, SGD, Adam, AdamW
    LR0 = 0.01                       # 初始学习率
    LRF = 0.01                       # 最终学习率 (LR0 * LRF)
    MOMENTUM = 0.937                 # SGD 动量
    WEIGHT_DECAY = 0.0005            # 权重衰减
    WARMUP_EPOCHS = 3.0              # 预热轮数
    CLOSE_MOSAIC = 10                # 最后N轮禁用马赛克

    # 其他选项
    AMP = True                        # 混合精度训练
    RESUME = False                    # 是否从中断处继续
    # ===============================================

    train_yolo_pose(
        model=MODEL,
        data_yaml=DATA_YAML,
        epochs=EPOCHS,
        batch=BATCH,
        imgsz=IMGSZ,
        workers=WORKERS,
        patience=PATIENCE,
        name=NAME,
        device=DEVICE,
        resume=RESUME,
        optimizer=OPTIMIZER,
        lr0=LR0,
        lrf=LRF,
        momentum=MOMENTUM,
        weight_decay=WEIGHT_DECAY,
        warmup_epochs=WARMUP_EPOCHS,
        close_mosaic=CLOSE_MOSAIC,
        amp=AMP,
    )


if __name__ == "__main__":
    main()
