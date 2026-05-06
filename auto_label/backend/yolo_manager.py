import os
import threading
import time
from typing import List, Optional, Dict, Any, Callable
import cv2
from ultralytics import YOLO
from models.annotation import Annotation, Shape, Point
from backend.utils import get_json_path, ensure_dir


class YOLOManager:
    def __init__(self):
        self.model: Optional[Any] = None
        self.model_path: Optional[str] = None
        self.is_training: bool = False
        self.is_inferencing: bool = False
        self._train_thread: Optional[threading.Thread] = None
        self._infer_thread: Optional[threading.Thread] = None
        self._train_epochs: int = 0
        self._train_project: str = ""
        self._train_name: str = ""

    def load_model(self, model_path: str) -> bool:
        try:
            if not os.path.exists(model_path):
                return False
            self.model = YOLO(model_path)
            self.model_path = model_path
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def train(
        self,
        data_yaml: str,
        epochs: int,
        batch: int,
        imgsz: int,
        workers: int,
        patience: int,
        project: str,
        name: str,
        device: str,
        progress_callback: Optional[Callable] = None,
        finished_callback: Optional[Callable] = None,
    ) -> Optional[str]:
        if self.is_training:
            return None

        self.is_training = True
        self._train_epochs = epochs
        self._train_project = project
        self._train_name = name

        def train_task():
            try:
                results = self.model.train(
                    data=data_yaml,
                    epochs=epochs,
                    batch=batch,
                    imgsz=imgsz,
                    workers=workers,
                    patience=patience,
                    project=project,
                    name=name,
                    device=device,
                    verbose=False,
                )

                best_model_path = os.path.join(project, name, "weights", "best.pt")

                if os.path.exists(best_model_path):
                    if finished_callback:
                        finished_callback(best_model_path)
                else:
                    if finished_callback:
                        finished_callback(None)

            except Exception as e:
                print(f"Training error: {e}")
                if finished_callback:
                    finished_callback(None)
            finally:
                self.is_training = False

        def progress_monitor():
            """监控训练进度，通过检查结果文件获取当前epoch"""
            last_epoch = 0
            while self.is_training:
                time.sleep(5)  # 每5秒检查一次
                results_dir = os.path.join(self._train_project, self._train_name)
                results_file = os.path.join(results_dir, "results.csv")

                if os.path.exists(results_file):
                    try:
                        with open(results_file, 'r') as f:
                            lines = f.readlines()
                            if len(lines) > 1:
                                # 最后一行是最新数据
                                last_line = lines[-1].strip()
                                parts = last_line.split(',')
                                if len(parts) > 0:
                                    try:
                                        current_epoch = int(float(parts[0].strip()))
                                        if progress_callback and current_epoch > last_epoch:
                                            last_epoch = current_epoch
                                            progress = current_epoch / self._train_epochs
                                            progress_callback(min(1.0, progress))
                                            print(f"Training progress: {current_epoch}/{self._train_epochs} ({progress*100:.1f}%)")
                                    except (ValueError, IndexError):
                                        pass
                    except Exception as e:
                        print(f"Error reading results.csv: {e}")

                # 检查是否训练结束
                best_path = os.path.join(results_dir, "weights", "best.pt")
                if os.path.exists(best_path) and not self.is_training:
                    break

        self._train_thread = threading.Thread(target=train_task, daemon=True)
        self._train_thread.start()

        # 启动进度监控线程
        progress_thread = threading.Thread(target=progress_monitor, daemon=True)
        progress_thread.start()

        return "training_started"

    def stop_training(self) -> None:
        self.is_training = False

    def predict(
        self,
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        max_det: int = 300,
        detect_keypoints: bool = True,
        conf_keypoints: float = 0.25,
    ) -> Optional[Annotation]:
        if not self.model:
            return None

        try:
            results = self.model.predict(
                image_path,
                conf=conf,
                iou=iou,
                max_det=max_det,
                verbose=False,
            )

            if not results:
                return None

            result = results[0]
            img = cv2.imread(image_path)
            height, width = img.shape[:2]

            annotation = Annotation(
                version="5.2.0",
                flags={},
                shapes=[],
                image_path=os.path.basename(image_path),
                image_data=None,
                image_height=height,
                image_width=width,
            )

            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                for i, (box, cls, conf) in enumerate(zip(boxes, classes, confs)):
                    x1, y1, x2, y2 = box
                    label = str(int(cls))

                    shape = Shape(
                        label=label,
                        shape_type="rectangle",
                        points=[Point(float(x1), float(y1)), Point(float(x2), float(y2))],
                    )
                    annotation.shapes.append(shape)

            if detect_keypoints and result.keypoints is not None:
                keypoints_data = result.keypoints.data.cpu().numpy()
                keypoints_conf = result.keypoints.conf.cpu().numpy()

                for i, (kp, kp_conf) in enumerate(zip(keypoints_data, keypoints_conf)):
                    for j, kp_point in enumerate(kp):
                        if kp_conf[j] >= conf_keypoints:
                            x = kp_point[0]
                            y = kp_point[1]
                            shape = Shape(
                                label=str(j),
                                shape_type="point",
                                points=[Point(float(x), float(y))],
                            )
                            annotation.shapes.append(shape)

            return annotation

        except Exception as e:
            print(f"Prediction error: {e}")
            return None

    def batch_predict(
        self,
        image_paths: List[str],
        output_dir: str,
        conf: float = 0.25,
        iou: float = 0.45,
        max_det: int = 300,
        detect_keypoints: bool = True,
        conf_keypoints: float = 0.25,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        finished_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        if self.is_inferencing:
            return 0

        self.is_inferencing = True
        ensure_dir(output_dir)

        def infer_task():
            success_count = 0
            total = len(image_paths)

            for i, img_path in enumerate(image_paths):
                annotation = self.predict(img_path, conf, iou, max_det, detect_keypoints, conf_keypoints)

                if annotation:
                    json_path = get_json_path(img_path)
                    output_json = os.path.join(output_dir, os.path.basename(json_path))
                    annotation.to_json(output_json)
                    success_count += 1

                if progress_callback:
                    progress_callback(i + 1, total)

            self.is_inferencing = False
            if finished_callback:
                finished_callback(success_count, total)

        self._infer_thread = threading.Thread(target=infer_task, daemon=True)
        self._infer_thread.start()
        return len(image_paths)

    def stop_inference(self) -> None:
        self.is_inferencing = False

    def get_model_info(self) -> Dict[str, Any]:
        if not self.model:
            return {}

        return {
            "model_path": self.model_path,
            "is_training": self.is_training,
            "is_inferencing": self.is_inferencing,
        }
