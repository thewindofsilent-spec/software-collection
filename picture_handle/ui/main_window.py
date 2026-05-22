from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.pipeline import Pipeline, PipelineStep
from processing.operation import Operation
from processing.registry import OPERATION_REGISTRY
from ui.widgets.image_viewer import ImageViewer, PixelInfo


SUPPORTED_IMAGE_FILTER = "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"


class PipelineWorkerSignals(QObject):
    started = Signal()
    finished = Signal(object, float)
    error = Signal(str)


class PipelineWorker(QRunnable):
    """Run a Pipeline in QThreadPool without blocking the UI thread."""

    def __init__(self, pipeline: Pipeline, image: np.ndarray) -> None:
        super().__init__()
        self.signals = PipelineWorkerSignals()
        self._pipeline = pipeline
        self._image = image.copy()

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        started_at = time.perf_counter()
        try:
            result = self._pipeline.execute(self._image, keep_snapshots=True)
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            self.signals.finished.emit(result, elapsed_ms)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class MainWindow(QMainWindow):
    """Main application window for the image processing desktop app."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("图像处理工作台")
        self.resize(1440, 900)

        self.thread_pool = QThreadPool.globalInstance()
        self.pipeline = Pipeline()
        self._image_paths: List[Path] = []
        self._images: Dict[Path, np.ndarray] = {}
        self._current_path: Optional[Path] = None
        self._current_image: Optional[np.ndarray] = None
        self._processed_image: Optional[np.ndarray] = None
        self._running = False

        self._build_actions()
        self._build_menu_bar()
        self._build_tool_bar()
        self._build_central_view()
        self._build_left_dock()
        self._build_right_dock()
        self._build_status_bar()
        self._connect_signals()

    def _build_actions(self) -> None:
        self.import_images_action = QAction("导入图片", self)
        self.import_folder_action = QAction("导入文件夹", self)
        self.export_action = QAction("导出结果", self)
        self.save_pipeline_action = QAction("保存流程", self)
        self.load_pipeline_action = QAction("加载流程", self)
        self.run_all_action = QAction("运行全部", self)
        self.clear_pipeline_action = QAction("清空流程", self)
        self.fit_action = QAction("适应窗口", self)
        self.actual_size_action = QAction("1:1", self)

        self.import_images_action.setShortcut("Ctrl+O")
        self.export_action.setShortcut("Ctrl+E")
        self.save_pipeline_action.setShortcut("Ctrl+S")
        self.run_all_action.setShortcut("Ctrl+R")

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.import_images_action)
        file_menu.addAction(self.import_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_pipeline_action)
        file_menu.addAction(self.load_pipeline_action)

        process_menu = self.menuBar().addMenu("处理")
        process_menu.addAction(self.run_all_action)
        process_menu.addAction(self.clear_pipeline_action)

        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_size_action)

    def _build_tool_bar(self) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setObjectName("mainToolBar")
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        toolbar.addAction(self.import_images_action)
        toolbar.addAction(self.import_folder_action)
        toolbar.addSeparator()
        toolbar.addAction(self.export_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_all_action)
        toolbar.addSeparator()
        toolbar.addAction(self.save_pipeline_action)
        toolbar.addAction(self.load_pipeline_action)

    def _build_central_view(self) -> None:
        self.original_viewer = ImageViewer()
        self.processed_viewer = ImageViewer()

        self.original_title = QLabel("原图")
        self.processed_title = QLabel("处理结果")
        self.original_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.original_title)
        left_layout.addWidget(self.original_viewer, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.processed_title)
        right_layout.addWidget(self.processed_viewer, 1)

        self.viewer_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewer_splitter.addWidget(left_panel)
        self.viewer_splitter.addWidget(right_panel)
        self.viewer_splitter.setStretchFactor(0, 1)
        self.viewer_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.viewer_splitter)

    def _build_left_dock(self) -> None:
        self.file_list = QListWidget()
        self.file_list.setIconSize(QSize(96, 72))
        self.file_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.left_dock = QDockWidget("文件 / 缩略图", self)
        self.left_dock.setObjectName("filesDock")
        self.left_dock.setWidget(self.file_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

    def _build_right_dock(self) -> None:
        right_root = QWidget()
        right_layout = QVBoxLayout(right_root)
        right_layout.setContentsMargins(8, 8, 8, 8)

        operation_row = QHBoxLayout()
        self.operation_combo = QComboBox()
        for operation_type, operation_cls in OPERATION_REGISTRY.items():
            self.operation_combo.addItem(operation_cls.name, operation_type)

        self.add_operation_button = QPushButton("添加")
        self.remove_operation_button = QPushButton("删除")
        operation_row.addWidget(self.operation_combo, 1)
        operation_row.addWidget(self.add_operation_button)
        operation_row.addWidget(self.remove_operation_button)

        reorder_row = QHBoxLayout()
        self.move_up_button = QPushButton("上移")
        self.move_down_button = QPushButton("下移")
        reorder_row.addWidget(self.move_up_button)
        reorder_row.addWidget(self.move_down_button)

        self.pipeline_list = QListWidget()
        self.pipeline_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.pipeline_list.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.parameter_title = QLabel("参数")
        self.parameter_stack = QStackedWidget()
        self.empty_parameter_panel = QLabel("请选择一个操作以编辑参数。")
        self.empty_parameter_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.parameter_stack.addWidget(self.empty_parameter_panel)

        right_layout.addLayout(operation_row)
        right_layout.addLayout(reorder_row)
        right_layout.addWidget(QLabel("处理流程"))
        right_layout.addWidget(self.pipeline_list, 1)
        right_layout.addWidget(self.parameter_title)
        right_layout.addWidget(self.parameter_stack, 1)

        self.right_dock = QDockWidget("处理流程编辑器", self)
        self.right_dock.setObjectName("pipelineDock")
        self.right_dock.setWidget(right_root)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)

    def _build_status_bar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)

        self.image_info_label = QLabel("未加载图像")
        self.pixel_info_label = QLabel("")
        self.elapsed_label = QLabel("耗时：--")
        self.thread_info_label = QLabel(f"线程：{self.thread_pool.maxThreadCount()}")

        status.addWidget(self.image_info_label, 2)
        status.addWidget(self.pixel_info_label, 2)
        status.addPermanentWidget(self.elapsed_label)
        status.addPermanentWidget(self.thread_info_label)

    def _connect_signals(self) -> None:
        self.import_images_action.triggered.connect(self.import_images)
        self.import_folder_action.triggered.connect(self.import_folder)
        self.export_action.triggered.connect(self.export_result)
        self.save_pipeline_action.triggered.connect(self.save_pipeline)
        self.load_pipeline_action.triggered.connect(self.load_pipeline)
        self.run_all_action.triggered.connect(self.run_pipeline)
        self.clear_pipeline_action.triggered.connect(self.clear_pipeline)
        self.fit_action.triggered.connect(self.fit_viewers)
        self.actual_size_action.triggered.connect(self.actual_size_viewers)

        self.file_list.currentItemChanged.connect(self._on_file_selected)
        self.add_operation_button.clicked.connect(self.add_selected_operation)
        self.remove_operation_button.clicked.connect(self.remove_selected_operation)
        self.move_up_button.clicked.connect(self.move_selected_operation_up)
        self.move_down_button.clicked.connect(self.move_selected_operation_down)
        self.pipeline_list.currentItemChanged.connect(self._on_pipeline_selection_changed)
        self.pipeline_list.model().rowsMoved.connect(self._sync_pipeline_from_list_order)

        self.original_viewer.mousePixelChanged.connect(self._show_pixel_info)
        self.processed_viewer.mousePixelChanged.connect(self._show_pixel_info)
        self.original_viewer.mouseLeftImage.connect(lambda: self.pixel_info_label.setText(""))
        self.processed_viewer.mouseLeftImage.connect(lambda: self.pixel_info_label.setText(""))

    @Slot()
    def import_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "导入图片", "", SUPPORTED_IMAGE_FILTER)
        if files:
            self._add_image_paths([Path(file) for file in files])

    @Slot()
    def import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "导入文件夹")
        if not folder:
            return

        extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
        paths = [path for path in Path(folder).iterdir() if path.suffix.lower() in extensions]
        self._add_image_paths(paths)

    @Slot()
    def export_result(self) -> None:
        if self._processed_image is None:
            QMessageBox.information(self, "导出", "当前没有可导出的处理结果。")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "导出结果", "", SUPPORTED_IMAGE_FILTER)
        if not file_path:
            return

        try:
            self._write_image(Path(file_path), self._processed_image)
            self.statusBar().showMessage(f"已导出：{file_path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    @Slot()
    def save_pipeline(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "保存流程", "", "流程配置 (*.json)")
        if not file_path:
            return

        try:
            Path(file_path).write_text(
                json.dumps(self.pipeline.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.statusBar().showMessage(f"流程已保存：{file_path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "保存流程失败", str(exc))

    @Slot()
    def load_pipeline(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "加载流程", "", "流程配置 (*.json)")
        if not file_path:
            return

        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
            self.pipeline = Pipeline.from_dict(data)
            self._refresh_pipeline_list()
            self.statusBar().showMessage(f"流程已加载：{file_path}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "加载流程失败", str(exc))

    @Slot()
    def run_pipeline(self) -> None:
        if self._current_image is None:
            QMessageBox.information(self, "运行流程", "请先导入并选择一张图片。")
            return
        if self._running:
            return

        worker = PipelineWorker(self._clone_pipeline(), self._current_image)
        worker.signals.started.connect(self._on_pipeline_started)
        worker.signals.finished.connect(self._on_pipeline_finished)
        worker.signals.error.connect(self._on_pipeline_error)
        self.thread_pool.start(worker)

    @Slot()
    def clear_pipeline(self) -> None:
        self.pipeline.clear()
        self._refresh_pipeline_list()

    @Slot()
    def add_selected_operation(self) -> None:
        operation_type = str(self.operation_combo.currentData())
        operation_cls = OPERATION_REGISTRY.get(operation_type)
        if operation_cls is None:
            QMessageBox.warning(self, "处理流程", f"未知操作：{operation_type}")
            return

        step_id = self.pipeline.add(operation_cls())
        self._refresh_pipeline_list(select_step_id=step_id)

    @Slot()
    def remove_selected_operation(self) -> None:
        item = self.pipeline_list.currentItem()
        if item is None:
            return
        self.pipeline.remove(str(item.data(Qt.ItemDataRole.UserRole)))
        self._refresh_pipeline_list()

    @Slot()
    def move_selected_operation_up(self) -> None:
        self._move_selected_operation(-1)

    @Slot()
    def move_selected_operation_down(self) -> None:
        self._move_selected_operation(1)

    def _move_selected_operation(self, delta: int) -> None:
        item = self.pipeline_list.currentItem()
        if item is None:
            return
        row = self.pipeline_list.row(item)
        new_row = row + delta
        if new_row < 0 or new_row >= len(self.pipeline.steps):
            return
        step_id = str(item.data(Qt.ItemDataRole.UserRole))
        self.pipeline.reorder(step_id, new_row)
        self._refresh_pipeline_list(select_step_id=step_id)

    def _add_image_paths(self, paths: List[Path]) -> None:
        for path in paths:
            if path in self._image_paths:
                continue

            try:
                image = self._read_image(path)
            except Exception as exc:
                QMessageBox.warning(self, "导入失败", f"{path}\n\n{exc}")
                continue

            self._image_paths.append(path)
            self._images[path] = image

            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setIcon(QIcon(self._make_thumbnail(image)))
            self.file_list.addItem(item)

        if self.file_list.count() > 0 and self.file_list.currentRow() < 0:
            self.file_list.setCurrentRow(0)

    def _on_file_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if current is None:
            return

        path = Path(str(current.data(Qt.ItemDataRole.UserRole)))
        image = self._images.get(path)
        if image is None:
            return

        self._current_path = path
        self._current_image = image
        self._processed_image = None
        self.original_viewer.set_image(image, color_space="BGR")
        self.processed_viewer.clear_image()
        height, width = image.shape[:2]
        channels = 1 if image.ndim == 2 else image.shape[2]
        self.image_info_label.setText(f"{path.name} | {width}x{height} | 通道数：{channels}")
        self.elapsed_label.setText("耗时：--")

    def _on_pipeline_selection_changed(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            self.parameter_stack.setCurrentWidget(self.empty_parameter_panel)
            return

        step_id = str(current.data(Qt.ItemDataRole.UserRole))
        step = self._find_step(step_id)
        if step is None:
            self.parameter_stack.setCurrentWidget(self.empty_parameter_panel)
            return

        widget = step.operation.get_widget()
        widget.setProperty("step_id", step_id)
        step.operation.parameterChanged.connect(lambda _params: self._mark_pipeline_dirty())
        self._replace_parameter_widget(widget)

    def _replace_parameter_widget(self, widget: QWidget) -> None:
        while self.parameter_stack.count() > 1:
            old_widget = self.parameter_stack.widget(1)
            self.parameter_stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.parameter_stack.addWidget(widget)
        self.parameter_stack.setCurrentWidget(widget)

    def _sync_pipeline_from_list_order(self) -> None:
        step_by_id = {step.step_id: step for step in self.pipeline.steps}
        ordered_steps: List[PipelineStep] = []
        for row in range(self.pipeline_list.count()):
            item = self.pipeline_list.item(row)
            step = step_by_id.get(str(item.data(Qt.ItemDataRole.UserRole)))
            if step is not None:
                ordered_steps.append(step)
        if len(ordered_steps) == len(self.pipeline.steps):
            self.pipeline.steps = ordered_steps
            self._refresh_pipeline_list()

    def _refresh_pipeline_list(self, *, select_step_id: Optional[str] = None) -> None:
        self.pipeline_list.blockSignals(True)
        self.pipeline_list.clear()
        for index, step in enumerate(self.pipeline.steps, start=1):
            item = QListWidgetItem(f"{index}. {step.operation.name}")
            item.setData(Qt.ItemDataRole.UserRole, step.step_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            self.pipeline_list.addItem(item)
            if select_step_id == step.step_id:
                self.pipeline_list.setCurrentItem(item)
        self.pipeline_list.blockSignals(False)

        if select_step_id:
            self._on_pipeline_selection_changed(self.pipeline_list.currentItem(), None)
        elif self.pipeline_list.count() == 0:
            self.parameter_stack.setCurrentWidget(self.empty_parameter_panel)

    def _find_step(self, step_id: str) -> Optional[PipelineStep]:
        for step in self.pipeline.steps:
            if step.step_id == step_id:
                return step
        return None

    def _clone_pipeline(self) -> Pipeline:
        return Pipeline.from_dict(deepcopy(self.pipeline.to_dict()))

    @Slot()
    def _on_pipeline_started(self) -> None:
        self._running = True
        self.run_all_action.setEnabled(False)
        self.statusBar().showMessage("正在运行处理流程...")

    @Slot(object, float)
    def _on_pipeline_finished(self, result: np.ndarray, elapsed_ms: float) -> None:
        self._running = False
        self.run_all_action.setEnabled(True)
        self._processed_image = result
        self.processed_viewer.set_image(result, color_space="BGR")
        self.elapsed_label.setText(f"耗时：{elapsed_ms:.1f} ms")
        self.statusBar().showMessage("处理流程运行完成", 3000)

    @Slot(str)
    def _on_pipeline_error(self, message: str) -> None:
        self._running = False
        self.run_all_action.setEnabled(True)
        self.statusBar().showMessage("处理流程运行失败", 3000)
        QMessageBox.critical(self, "处理流程失败", message)

    @Slot(object)
    def _show_pixel_info(self, info: PixelInfo) -> None:
        self.pixel_info_label.setText(
            f"坐标=({info.x}, {info.y}) | BGR={info.bgr} | HSV={info.hsv}"
        )

    def fit_viewers(self) -> None:
        self.original_viewer.fit_to_view()
        self.processed_viewer.fit_to_view()

    def actual_size_viewers(self) -> None:
        self.original_viewer.actual_size()
        self.processed_viewer.actual_size()

    def _mark_pipeline_dirty(self) -> None:
        self.statusBar().showMessage("流程参数已变更", 1200)

    @staticmethod
    def _read_image(path: Path) -> np.ndarray:
        data = np.fromfile(str(path), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError("读取图像失败。")
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 3:
            return image
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        raise ValueError(f"不支持的图像尺寸或通道：{image.shape}")

    @staticmethod
    def _write_image(path: Path, image: np.ndarray) -> None:
        extension = path.suffix or ".png"
        ok, buffer = cv2.imencode(extension, image)
        if not ok:
            raise ValueError(f"无法编码为 {extension} 格式")
        buffer.tofile(str(path))

    @staticmethod
    def _make_thumbnail(image: np.ndarray) -> QPixmap:
        preview = image
        height, width = preview.shape[:2]
        max_edge = max(width, height)
        if max_edge > 160:
            scale = 160.0 / max_edge
            preview = cv2.resize(
                preview,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        return ImageViewer.cv_mat_to_qpixmap(preview, color_space="BGR")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
