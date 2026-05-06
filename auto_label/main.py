"""
AutoLabel - 半监督自动标注工具
主程序入口：负责QML引擎加载、Python对象注册到QML上下文

QML与Python通信机制：
- QObject子类：通过Signal/Slot/Property与QML双向通信
- QQuickImageProvider：提供图像给QML的Image组件
- 所有耗时操作（训练、批量推理）在后台线程执行，通过信号更新UI
"""

import os
import sys
from typing import List, Optional
from PySide6.QtCore import QObject, QUrl, QSize, Signal, Slot, Property
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

<<<<<<< HEAD
import cv2
=======
from PIL import Image
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55

from backend.yolo_manager import YOLOManager
from backend.annotation_manager import AnnotationManager
from backend.dataset_converter import DatasetConverter
from backend.utils import list_images_in_directory, get_json_path
from models.annotation import Point
from config.settings_manager import settings


# ==================== 图像提供者 ====================
class ImageProvider(QQuickImageProvider):
    """
    为QML的Image组件提供图像数据
    使用QPixmap格式，支持异步加载
    """

    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)
        self.current_image: Optional[QImage] = None
        self.current_path: Optional[str] = None

    def requestPixmap(self, id: str, size: QSize, requestedSize: QSize):
        """返回当前图像的Pixmap"""
        if self.current_image and not self.current_image.isNull():
            pixmap = QPixmap.fromImage(self.current_image)
            return pixmap
        return QPixmap()

    def set_image(self, path: str):
        """加载指定路径的图像"""
        if os.path.exists(path):
            self.current_image = QImage(path)
            self.current_path = path

    def clear(self):
        """清除当前图像"""
        self.current_image = None
        self.current_path = None


# ==================== 图像列表项 ====================
class ImageItem(QObject):
    """
    代表列表中的一个图像项
    暴露path、name、annotated属性给QML
    """

    def __init__(self, path: str, annotated: bool = False, parent=None):
        super().__init__(parent)
        self._path = path
        self._annotated = annotated

    def _get_path(self):
        return self._path

    def _get_name(self):
        return os.path.basename(self._path)

    def _get_annotated(self):
        return self._annotated

    # QML可访问的属性
    path = Property(str, _get_path, constant=True)
    name = Property(str, _get_name, constant=True)
    annotated = Property(bool, _get_annotated, constant=True)


# ==================== 图像列表模型 ====================
class ImageListModel(QObject):
    """
    图像列表的数据模型
    支持count和selectedIndex属性通知QML刷新
    """

    countChanged = Signal()
    selectedIndexChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ImageItem] = []
        self._selected_index: int = -1

    def append(self, item: ImageItem):
        """添加图像项"""
        self._items.append(item)
        self.countChanged.emit()

    def clear(self):
        """清空列表"""
        self._items.clear()
        self._selected_index = -1
        self.countChanged.emit()
        self.selectedIndexChanged.emit()

    def at(self, index: int) -> Optional[ImageItem]:
        """获取指定索引的图像项"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def _get_count(self) -> int:
        return len(self._items)

    def _get_selected_index(self) -> int:
        return self._selected_index

    def _set_selected_index(self, index: int):
        """设置选中索引，触发信号通知QML"""
        if 0 <= index < len(self._items):
            self._selected_index = index
            self.selectedIndexChanged.emit()

    count = Property(int, _get_count, notify=countChanged)
    selectedIndex = Property(int, _get_selected_index, _set_selected_index, notify=selectedIndexChanged)


# ==================== 主控制器 ====================
class AutoLabelController(QObject):
    """
    应用主控制器，协调各个模块
    所有QML可调用的Slot都在此类中定义
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # 子模块初始化
        self.yolo_manager = YOLOManager()
        self.annotation_manager = AnnotationManager()
        self.dataset_converter = DatasetConverter()
        self.image_provider = ImageProvider()
        self.image_list_model = ImageListModel()

        # 状态变量
        self._current_dir: str = ""
        self._model_loaded: bool = False
        self._is_training: bool = False
        self._is_auto_labeling: bool = False
        self._train_progress: float = 0.0
        self._auto_label_progress: float = 0.0
        self._current_image_size = (0, 0)
        self._status_message: str = ""

        # 初始化配置管理器
        self._init_settings()

    def _init_settings(self):
        """初始化配置，设置默认配置路径"""
        # 获取程序所在目录
        app_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(app_dir, "config", "settings.json")
        settings.set_config_path(config_path)
        settings.load()

        # 加载上次的路径配置
        self._current_dir = settings.get("paths.last_image_dir", "")

    # ==================== Qt信号定义 ====================
    modelLoadedChanged = Signal()
    trainingStarted = Signal()
    trainingFinished = Signal(str)
    trainingProgressChanged = Signal()
    autoLabelStarted = Signal()
    autoLabelFinished = Signal(int, int)
    autoLabelProgressChanged = Signal()
    imageListChanged = Signal()
    annotationChanged = Signal()
    statusMessageChanged = Signal()
    configChanged = Signal()

    # ==================== 属性访问器 ====================
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

    # ==================== QML可访问的属性 ====================
    modelLoaded = Property(bool, _get_model_loaded, _set_model_loaded, modelLoadedChanged)
    isTraining = Property(bool, _get_is_training, notify=trainingStarted)
    isAutoLabeling = Property(bool, _get_is_auto_labeling, notify=autoLabelStarted)
    trainProgress = Property(float, _get_train_progress, notify=trainingProgressChanged)
    autoLabelProgress = Property(float, _get_auto_label_progress, notify=autoLabelProgressChanged)
    statusMessage = Property(str, _get_status_message, notify=statusMessageChanged)
    imageListModel = Property(QObject, lambda self: self.image_list_model, constant=True)

    # ==================== 配置相关Slot ====================
    @Slot(str, result=bool)
    def loadConfig(self, configPath: str) -> bool:
        """加载配置文件"""
        configPath = self._normalize_folder_path(configPath)
        result = settings.load(configPath)
        if result:
            self._set_status_message(f"配置已加载: {configPath}")
            self.configChanged.emit()
        else:
            self._set_status_message("配置加载失败或文件不存在")
        return result

    @Slot(str, result=bool)
    def saveConfig(self, configPath: str) -> bool:
        """保存配置文件"""
        configPath = self._normalize_folder_path(configPath)
        result = settings.save(configPath)
        if result:
            self._set_status_message(f"配置已保存: {configPath}")
        else:
            self._set_status_message("配置保存失败")
        return result

    @Slot(result=str)
    def getConfigPath(self) -> str:
        """获取当前配置路径"""
        return settings.get_config_path()

    @Slot(str, result="QVariant")
    def getConfigValue(self, key: str):
        """获取配置值"""
        return settings.get(key)

    @Slot(str, "QVariant")
    def setConfigValue(self, key: str, value):
        """设置配置值"""
        settings.set(key, value)

    @Slot(str)
    def setStatusMessage(self, msg: str):
        """设置状态栏消息"""
        self._set_status_message(msg)

    # ==================== 文件操作Slot ====================
    def _normalize_folder_path(self, path) -> str:
        """将QUrl或路径字符串转换为标准Windows路径"""
        if path is None:
            return ""
        # 如果是QUrl对象，转换为本地路径
        if isinstance(path, QUrl):
            path = path.toLocalFile()
        # 如果不是字符串，直接返回
        if not isinstance(path, str):
            return str(path)
        # 移除各种 file:// 格式的前缀
        for prefix in ["file:///", "file://", "file:/", "file:"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        # 将所有反斜杠和正斜杠转为反斜杠（Windows标准）
        path = path.replace("/", "\\")
        # 清理多余的反斜杠（但保留 UNC 的 \\ 前缀）
        if path.startswith("\\\\"):
            pass  # UNC 路径保留
        elif path.startswith("\\"):
            path = path[1:]
        # 清理空的 path
        if not path:
            return ""
        # 清理重复的分隔符
        while "\\\\" in path:
            path = path.replace("\\\\", "\\")
        return path

    @Slot(str)
    def loadFolder(self, folderPath: str):
        """加载文件夹中的所有图像"""
        folderPath = self._normalize_folder_path(folderPath)
        if not os.path.isdir(folderPath):
            return
        self._current_dir = folderPath
        settings.set("paths.last_image_dir", folderPath)
        self.image_list_model.clear()

        # 递归获取所有图像
        images = list_images_in_directory(folderPath, recursive=True)

        for img_path in images:
            json_path = get_json_path(img_path)
            # 根据是否存在同名json判断是否已标注
            annotated = os.path.exists(json_path)
            item = ImageItem(img_path, annotated)
            self.image_list_model.append(item)

        self.imageListChanged.emit()
        self._set_status_message(f"已加载 {len(images)} 张图像")

    @Slot(int)
    def selectImage(self, index: int):
        """选择指定索引的图像，加载其标注"""
        if index < 0 or index >= self.image_list_model.count:
            return
        item = self.image_list_model.at(index)
        if not item:
            return

        # 更新图像提供者
        self.image_provider.set_image(item.path)

        # 加载标注（如果存在）
        self.annotation_manager.load_annotation(item.path)

        # 如果没有标注文件，创建空标注
        if not self.annotation_manager.current_annotation:
            self.annotation_manager.create_empty_annotation(item.path)

        # 更新选中索引
        self.image_list_model._set_selected_index(index)

        # 获取图像尺寸
<<<<<<< HEAD
        img = cv2.imread(item.path)
        self._current_image_size = img.shape[1], img.shape[0]
        self.annotation_manager.set_image_size(*self._current_image_size)
=======
        img = Image.open(item.path)
        self._current_image_size = img.size
        self.annotation_manager.set_image_size(*self._current_image_size)
        img.close()
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55

        self.annotationChanged.emit()

    @Slot(str, result=bool)
    def loadModel(self, modelPath: str) -> bool:
        """加载YOLO模型"""
        modelPath = self._normalize_folder_path(modelPath)
        if not os.path.exists(modelPath):
            self._set_status_message("模型文件不存在")
            return False
        result = self.yolo_manager.load_model(modelPath)
        self._set_model_loaded(result)
        settings.set("paths.last_model_path", modelPath)
        self._set_status_message(f"模型已加载: {os.path.basename(modelPath)}" if result else "模型加载失败")
        return result

    # ==================== 训练相关Slot ====================
    @Slot(str, int, int, int, int, int, str, str)
    def startTraining(self, dataYaml: str, epochs: int, batch: int, imgsz: int, workers: int, patience: int, project: str, name: str):
        """启动YOLO训练（后台线程）"""
        if self._is_training:
            return
        if not self._model_loaded or not self.yolo_manager.model:
            self._set_status_message("请先加载YOLO模型")
            return
        if not dataYaml:
            self._set_status_message("请选择数据集YAML文件")
            return
        dataYaml = self._normalize_folder_path(dataYaml)
        self._is_training = True
        self.trainingStarted.emit()

        # 保存训练参数到配置
        settings.set("training.epochs", epochs)
        settings.set("training.batch", batch)
        settings.set("training.imgsz", imgsz)
        settings.set("training.workers", workers)
        settings.set("training.patience", patience)
        settings.set("training.project", project)
        settings.set("training.name", name)
        settings.set("paths.last_dataset_yaml", dataYaml)

        def on_finished(best_path):
            """训练完成回调"""
            self._is_training = False
            self._train_progress = 1.0
            self.trainingProgressChanged.emit()
            self.trainingFinished.emit(best_path or "")
            self._set_status_message("训练完成" if best_path else "训练失败")

        def on_progress(progress):
            """进度更新回调"""
            self._train_progress = progress
            self.trainingProgressChanged.emit()

        # 后台线程执行训练
        self.yolo_manager.train(
            data_yaml=dataYaml, epochs=epochs, batch=batch, imgsz=imgsz,
            workers=workers, patience=patience, project=project, name=name,
            device="0", progress_callback=on_progress, finished_callback=on_finished,
        )

    # ==================== 自动标注Slot ====================
<<<<<<< HEAD
    @Slot(str, str, float, float, int, bool, float)
    def startAutoLabel(self, imageDir: str, outputDir: str, conf: float, iou: float, maxDet: int, detectKeypoints: bool, confKeypoints: float):
=======
    @Slot(str, str, float, float, int)
    def startAutoLabel(self, imageDir: str, outputDir: str, conf: float, iou: float, maxDet: int):
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        """启动批量自动标注（后台线程）"""
        if self._is_auto_labeling or not self._model_loaded:
            return

        imageDir = self._normalize_folder_path(imageDir)
        outputDir = self._normalize_folder_path(outputDir)

        # 保存自动标注参数
        settings.set("auto_label.conf", conf)
        settings.set("auto_label.iou", iou)
        settings.set("auto_label.max_det", maxDet)
<<<<<<< HEAD
        settings.set("auto_label.detect_keypoints", detectKeypoints)
        settings.set("auto_label.conf_keypoints", confKeypoints)
=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        settings.set("paths.last_output_dir", outputDir)

        images = list_images_in_directory(imageDir)
        if not images:
            self._set_status_message("目录中没有找到图像")
            return

        self._is_auto_labeling = True
        self.autoLabelStarted.emit()
        self._set_status_message("自动标注中...")

        def on_progress(current, total):
            """进度更新回调"""
            self._auto_label_progress = current / total
            self.autoLabelProgressChanged.emit()

        def on_finished(success_count, total):
            """批量完成回调"""
            self._is_auto_labeling = False
            self._auto_label_progress = 1.0
            self.autoLabelProgressChanged.emit()
            self.autoLabelFinished.emit(success_count, total)
            self._set_status_message(f"自动标注完成: {success_count}/{total} 张")

        # 后台线程执行批量推理
        self.yolo_manager.batch_predict(
            image_paths=images, output_dir=outputDir, conf=conf, iou=iou,
<<<<<<< HEAD
            max_det=maxDet, detect_keypoints=detectKeypoints, conf_keypoints=confKeypoints,
            progress_callback=on_progress, finished_callback=on_finished,
=======
            max_det=maxDet, progress_callback=on_progress, finished_callback=on_finished,
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        )

    # ==================== 数据集转换Slot ====================
    @Slot(str, str, bool, result=bool)
    def convertDataset(self, imageDir: str, outputDir: str, copyImages: bool) -> bool:
        """将LabelMe标注转换为YOLO格式"""
        imageDir = self._normalize_folder_path(imageDir)
        outputDir = self._normalize_folder_path(outputDir)
        settings.set("paths.last_output_dir", outputDir)
        result = self.dataset_converter.convert_labelme_to_yolo(
            image_dir=imageDir, output_dir=outputDir, copy_images=copyImages
        )
        self._set_status_message(f"数据集已转换到 {outputDir}" if result else "数据集转换失败")
        return result

    # ==================== 标注保存Slot ====================
    @Slot(str, result=bool)
    def saveCurrentAnnotation(self, imagePath: str) -> bool:
        """保存当前图像的标注到JSON文件"""
        if not self.annotation_manager.current_annotation:
            return False
        result = self.annotation_manager.save_annotation(self.annotation_manager.current_annotation, imagePath)
        if result:
            idx = self.image_list_model._get_selected_index()
            if idx >= 0:
                item = self.image_list_model.at(idx)
                if item:
                    item._annotated = True
                    self.annotationChanged.emit()
        return result

    # ==================== 形状操作Slot ====================
    @Slot(int, str, float, float, float, float)
    def addRectangle(self, index: int, label: str, x1: float, y1: float, x2: float, y2: float):
        """添加矩形框"""
        if index < 0:
            return
        self.annotation_manager.add_rectangle(label, x1, y1, x2, y2)
        self.annotationChanged.emit()

    @Slot(int, str, float, float)
    def addPoint(self, index: int, label: str, x: float, y: float):
        """添加关键点"""
        if index < 0:
            return
        self.annotation_manager.add_point(label, x, y)
        self.annotationChanged.emit()

    @Slot(int, int)
    def removeShape(self, index: int, shapeIndex: int):
        """删除指定形状"""
        if self.annotation_manager.remove_shape(shapeIndex):
            self.annotationChanged.emit()

    @Slot(int, int, str, float, float, float, float)
    def updateRectangle(self, index: int, shapeIndex: int, label: str, x1: float, y1: float, x2: float, y2: float):
        """更新矩形框"""
        shapes = self.annotation_manager.get_shapes()
        if 0 <= shapeIndex < len(shapes):
            shapes[shapeIndex].label = label
            shapes[shapeIndex].points = [Point(x1, y1), Point(x2, y2)]
            self.annotationChanged.emit()

    @Slot(int, int, str, float, float)
    def updatePoint(self, index: int, shapeIndex: int, label: str, x: float, y: float):
        """更新关键点"""
        shapes = self.annotation_manager.get_shapes()
        if 0 <= shapeIndex < len(shapes):
            shapes[shapeIndex].label = label
            shapes[shapeIndex].points = [Point(x, y)]
            self.annotationChanged.emit()

    # ==================== 查询Slot ====================
    @Slot(result=int)
    def getImageCount(self) -> int:
        """获取图像列表数量"""
        return self.image_list_model.count

    @Slot(int, result="QVariant")
    def getImageAt(self, index: int):
        """获取指定索引的图像数据"""
        item = self.image_list_model.at(index)
        if item:
            return {"path": item.path, "name": item.name, "annotated": item.annotated}
        return None

    @Slot(result=int)
    def getShapeCount(self) -> int:
        """获取当前图像的形状数量"""
        return len(self.annotation_manager.get_shapes())

    @Slot(int, result="QVariant")
    def getShape(self, shapeIndex: int):
        """获取指定索引的形状数据"""
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
        """获取当前图像宽度"""
        return self._current_image_size[0]

    @Slot(result=int)
    def getImageHeight(self) -> int:
        """获取当前图像高度"""
        return self._current_image_size[1]

    # ==================== 窗口关闭时保存配置 ====================
    def saveSettingsOnExit(self):
        """程序退出时保存配置"""
        if settings.get_config_path():
            settings.save()


# ==================== 程序入口 ====================
if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("AutoLabel")
    app.setApplicationName("AutoLabel")

    # 创建QML引擎
    engine = QQmlApplicationEngine()

    # 创建控制器并注册到QML上下文
    controller = AutoLabelController()
    engine.rootContext().setContextProperty("controller", controller)

    # 注册图像提供者
    engine.addImageProvider("imageProvider", controller.image_provider)

    # 加载主QML文件
    qml_file = os.path.join(os.path.dirname(__file__), "main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    # 程序退出前保存配置
    controller.saveSettingsOnExit()
    sys.exit(exit_code)
