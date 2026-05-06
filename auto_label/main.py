import os
import sys
import traceback
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, QUrl, QThread, QSize, Signal, Slot, Property
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

from PIL import Image

from backend.yolo_manager import YOLOManager
from backend.annotation_manager import AnnotationManager
from backend.dataset_converter import DatasetConverter
from backend.utils import list_images_in_directory, get_json_path
from models.annotation import Annotation, Shape, Point


class ImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)
        self.current_image: Optional[QImage] = None
        self.current_path: Optional[str] = None

    def requestImage(self, id: str, size: QSize, requestedSize: QSize):
        if self.current_image and not self.current_image.isNull():
            return self.current_image, self.current_image.size()
        return QImage(), QSize()

    def set_image(self, path: str):
        if os.path.exists(path):
            self.current_image = QImage(path)
            self.current_path = path

    def clear(self):
        self.current_image = None
        self.current_path = None


class ImageItem(QObject):
    def __init__(self, path: str, annotated: bool = False, parent=None):
        super().__init__(parent)
        self._path = path
        self._annotated = annotated
        self._selected = False

    def _get_name(self):
        return os.path.basename(self._path)

    def _get_path(self):
        return self._path

    def _get_annotated(self):
        return self._annotated

    def _get_selected(self):
        return self._selected

    def _set_selected(self, value):
        self._selected = value
        self.selectedChanged.emit()

    selectedChanged = Signal()

    path = Property(str, _get_path, constant=True)
    name = Property(str, _get_name, constant=True)
    annotated = Property(bool, _get_annotated, constant=True)
    selected = Property(bool, _get_selected, _set_selected, notify=selectedChanged)


class ImageListModel(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ImageItem] = []
        self._selected_index: int = -1

    def append(self, item: ImageItem):
        self._items.append(item)
        self.countChanged.emit()

    def insert(self, index: int, item: ImageItem):
        self._items.insert(index, item)
        self.countChanged.emit()

    def remove(self, index: int):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self.countChanged.emit()

    def clear(self):
        self._items.clear()
        self._selected_index = -1
        self.countChanged.emit()
        self.selectedIndexChanged.emit()

    def at(self, index: int) -> Optional[ImageItem]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def _get_count(self) -> int:
        return len(self._items)

    def _get_selected_index(self) -> int:
        return self._selected_index

    def _set_selected_index(self, index: int):
        if 0 <= index < len(self._items):
            self._selected_index = index
            self.selectedIndexChanged.emit()

    count = Property(int, _get_count, notify=countChanged)
    selectedIndex = Property(int, _get_selected_index, _set_selected_index, notify=selectedIndexChanged)

    countChanged = Signal()
    selectedIndexChanged = Signal()


class AutoLabelController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yolo_manager = YOLOManager()
        self.annotation_manager = AnnotationManager()
        self.dataset_converter = DatasetConverter()

        self.image_provider = ImageProvider()
        self.image_list_model = ImageListModel()

        self._current_dir: str = ""
        self._model_loaded: bool = False
        self._is_training: bool = False
        self._is_auto_labeling: bool = False
        self._train_progress: float = 0.0
        self._auto_label_progress: float = 0.0
        self._current_image_size = (0, 0)

    @Signal
    def modelLoadedChanged(self):
        pass

    @Signal
    def trainingStarted(self):
        pass

    @Signal
    def trainingFinished(self, modelPath: str):
        pass

    @Signal
    def trainingProgressChanged(self):
        pass

    @Signal
    def autoLabelStarted(self):
        pass

    @Signal
    def autoLabelFinished(self, successCount: int, total: int):
        pass

    @Signal
    def autoLabelProgressChanged(self):
        pass

    @Signal
    def imageListChanged(self):
        pass

    @Signal
    def annotationChanged(self):
        pass

    @Signal
    def statusMessageChanged(self):
        pass

    def _get_model_loaded(self) -> bool:
        return self._model_loaded

    def _set_model_loaded(self, value: bool):
        self._model_loaded = value
        self.modelLoadedChanged.emit()

    def _get_is_training(self) -> bool:
        return self._is_training

    def _get_is_auto_labeling(self) -> bool:
        return self._is_auto_labeling

    def _get_train_progress(self) -> float:
        return self._train_progress

    def _get_auto_label_progress(self) -> float:
        return self._auto_label_progress

    def _get_status_message(self) -> str:
        return self._status_message

    def _set_status_message(self, msg: str):
        self._status_message = msg
        self.statusMessageChanged.emit()

    modelLoaded = Property(bool, _get_model_loaded, notify=modelLoadedChanged)
    isTraining = Property(bool, _get_is_training, notify=trainingStarted)
    isAutoLabeling = Property(bool, _get_is_auto_labeling, notify=autoLabelStarted)
    trainProgress = Property(float, _get_train_progress, notify=trainingProgressChanged)
    autoLabelProgress = Property(float, _get_auto_label_progress, notify=autoLabelProgressChanged)
    statusMessage = Property(str, _get_status_message, notify=statusMessageChanged)

    @Slot(str)
    def loadFolder(self, folderPath: str):
        if not os.path.isdir(folderPath):
            return

        self._current_dir = folderPath
        self.image_list_model.clear()

        images = list_images_in_directory(folderPath, recursive=True)

        for img_path in images:
            json_path = get_json_path(img_path)
            annotated = os.path.exists(json_path)
            item = ImageItem(img_path, annotated)
            self.image_list_model.append(item)

        self.imageListChanged.emit()
        self._set_status_message(f"Loaded {len(images)} images")

    @Slot(int)
    def selectImage(self, index: int):
        if index < 0 or index >= self.image_list_model.count:
            return

        item = self.image_list_model.at(index)
        if not item:
            return

        self.image_provider.set_image(item.path)
        self.annotation_manager.load_annotation(item.path)

        if not self.annotation_manager.current_annotation:
            self.annotation_manager.create_empty_annotation(item.path)

        self.image_list_model.selectedIndex = index

        img = Image.open(item.path)
        self._current_image_size = img.size
        self.annotation_manager.set_image_size(*self._current_image_size)
        img.close()

        self.annotationChanged.emit()

    @Slot(str, result=bool)
    def loadModel(self, modelPath: str):
        result = self.yolo_manager.load_model(modelPath)
        self._set_model_loaded(result)
        if result:
            self._set_status_message(f"Model loaded: {os.path.basename(modelPath)}")
        else:
            self._set_status_message("Failed to load model")
        return result

    @Slot(str, int, int, int, int, int, str, str)
    def startTraining(
        self, dataYaml: str, epochs: int, batch: int, imgsz: int, workers: int, patience: int, project: str, name: str
    ):
        if self._is_training:
            return

        self._is_training = True
        self.trainingStarted.emit()

        def on_finished(best_path):
            self._is_training = False
            self._train_progress = 1.0
            self.trainingProgressChanged.emit()
            self.trainingFinished.emit(best_path or "")
            self._set_status_message("Training finished" if best_path else "Training failed")

        self.yolo_manager.train(
            data_yaml=dataYaml,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            workers=workers,
            patience=patience,
            project=project,
            name=name,
            device="0",
            finished_callback=on_finished,
        )

    @Slot(str, str, float, float, int)
    def startAutoLabel(self, imageDir: str, outputDir: str, conf: float, iou: float, maxDet: int):
        if self._is_auto_labeling or not self._model_loaded:
            return

        images = list_images_in_directory(imageDir)
        if not images:
            self._set_status_message("No images found in directory")
            return

        self._is_auto_labeling = True
        self.autoLabelStarted.emit()
        self._set_status_message("Auto labeling in progress...")

        processed = [0]

        def on_progress(current, total):
            processed[0] = current
            self._auto_label_progress = current / total
            self.autoLabelProgressChanged.emit()

        def on_finished(success_count, total):
            self._is_auto_labeling = False
            self._auto_label_progress = 1.0
            self.autoLabelProgressChanged.emit()
            self.autoLabelFinished.emit(success_count, total)
            self._set_status_message(f"Auto labeling done: {success_count}/{total} success")

        self.yolo_manager.batch_predict(
            image_paths=images,
            output_dir=outputDir,
            conf=conf,
            iou=iou,
            max_det=maxDet,
            progress_callback=on_progress,
            finished_callback=on_finished,
        )

    @Slot(str, str, bool, result=bool)
    def convertDataset(self, imageDir: str, outputDir: str, copyImages: bool) -> bool:
        result = self.dataset_converter.convert_labelme_to_yolo(
            image_dir=imageDir, output_dir=outputDir, copy_images=copyImages
        )
        if result:
            self._set_status_message(f"Dataset converted to {outputDir}")
        else:
            self._set_status_message("Dataset conversion failed")
        return result

    @Slot(str, result=bool)
    def saveCurrentAnnotation(self, imagePath: str) -> bool:
        if not self.annotation_manager.current_annotation:
            return False
        result = self.annotation_manager.save_annotation(
            self.annotation_manager.current_annotation, imagePath
        )
        if result:
            idx = self.image_list_model.selectedIndex
            if idx >= 0:
                item = self.image_list_model.at(idx)
                if item:
                    item._annotated = True
                    self.annotationChanged.emit()
        return result

    @Slot(int, str, float, float, float, float)
    def addRectangle(self, index: int, label: str, x1: float, y1: float, x2: float, y2: float):
        if index < 0:
            return
        shape = self.annotation_manager.add_rectangle(label, x1, y1, x2, y2)
        self.annotationChanged.emit()

    @Slot(int, str, float, float)
    def addPoint(self, index: int, label: str, x: float, y: float):
        if index < 0:
            return
        shape = self.annotation_manager.add_point(label, x, y)
        self.annotationChanged.emit()

    @Slot(int, int)
    def removeShape(self, index: int, shapeIndex: int):
        if self.annotation_manager.remove_shape(shapeIndex):
            self.annotationChanged.emit()

    @Slot(int, int, str, float, float, float, float)
    def updateRectangle(
        self, index: int, shapeIndex: int, label: str, x1: float, y1: float, x2: float, y2: float
    ):
        shapes = self.annotation_manager.get_shapes()
        if 0 <= shapeIndex < len(shapes):
            shapes[shapeIndex].label = label
            shapes[shapeIndex].points = [Point(x1, y1), Point(x2, y2)]
            self.annotationChanged.emit()

    @Slot(int, int, str, float, float)
    def updatePoint(self, index: int, shapeIndex: int, label: str, x: float, y: float):
        shapes = self.annotation_manager.get_shapes()
        if 0 <= shapeIndex < len(shapes):
            shapes[shapeIndex].label = label
            shapes[shapeIndex].points = [Point(x, y)]
            self.annotationChanged.emit()

    @Slot(result=int)
    def getShapeCount(self) -> int:
        return len(self.annotation_manager.get_shapes())

    @Slot(int, result=object)
    def getShape(self, shapeIndex: int) -> Optional[Dict]:
        shapes = self.annotation_manager.get_shapes()
        if 0 <= shapeIndex < len(shapes):
            s = shapes[shapeIndex]
            return {
                "label": s.label,
                "shapeType": s.shape_type,
                "points": [[p.x, p.y] for p in s.points],
            }
        return None

    @Slot(result=int)
    def getImageWidth(self) -> int:
        return self._current_image_size[0]

    @Slot(result=int)
    def getImageHeight(self) -> int:
        return self._current_image_size[1]


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("AutoLabel")
    app.setApplicationName("AutoLabel")

    engine = QQmlApplicationEngine()
    controller = AutoLabelController()
    engine.rootContext().setContextProperty("controller", controller)
    engine.addImageProvider("imageProvider", controller.image_provider)

    qml_file = os.path.join(os.path.dirname(__file__), "main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    sys.exit(exit_code)
