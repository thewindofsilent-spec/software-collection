"""MVC 中的 View 层。

MainWindow 只负责界面创建、用户输入采集和展示 Controller 发来的状态。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from controller import MainController
from models import AppConfig, EXTRACT_MODES, MODE_FPS, MODE_INTERVAL, MODE_RANGE, MODE_TOTAL
from utils import ensure_ffmpeg


class MainWindow(QMainWindow):
    """视频转图片工具主窗口 View。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Frame Exporter - 视频转图片工具")
        self.resize(1180, 760)
        self.setAcceptDrops(True)

        self.controller = MainController(self)
        self.mode_rows: dict[str, tuple[QWidget, QWidget]] = {}

        self._build_actions()
        self._build_ui()
        self._connect_controller()
        self._restore_persisted_state()
        self._load_style()
        self._check_ffmpeg_on_startup()

    def _build_actions(self) -> None:
        """创建顶部工具栏。"""
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        open_action = QAction("打开视频", self)
        open_action.triggered.connect(self.open_files)
        toolbar.addAction(open_action)

        output_action = QAction("输出文件夹", self)
        output_action.triggered.connect(self.choose_output_dir)
        toolbar.addAction(output_action)

        toolbar.addSeparator()

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

    def _build_ui(self) -> None:
        """创建主界面布局。"""
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        self.setCentralWidget(central)

        splitter = QSplitter(Qt.Horizontal, self)
        root.addWidget(splitter, stretch=8)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(self._build_bottom_panel(), stretch=3)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("拖拽视频文件到窗口，或点击“打开视频”。")

    def _build_left_panel(self) -> QWidget:
        """左侧视频列表与信息预览区。"""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(10)

        title = QLabel("视频队列")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.video_list = QListWidget(self)
        self.video_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.video_list.currentRowChanged.connect(self.controller.update_preview)
        layout.addWidget(self.video_list, stretch=7)

        self.info_label = QLabel("暂无视频。\n\n支持拖拽文件或文件夹批量添加。")
        self.info_label.setObjectName("InfoPanel")
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label, stretch=3)

        remove_btn = QPushButton("移除选中")
        remove_btn.clicked.connect(self.remove_selected)
        layout.addWidget(remove_btn)
        return panel

    def _build_right_panel(self) -> QWidget:
        """右侧参数表单。"""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("导出参数")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        form_holder = QWidget(self)
        form_holder.setObjectName("FormPanel")
        form = QFormLayout(form_holder)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(EXTRACT_MODES)
        self.mode_combo.currentTextChanged.connect(self.update_mode_fields)
        form.addRow("提取模式", self.mode_combo)

        self.fps_spin = QSpinBox(self)
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(1)
        self._add_mode_row(form, "fps", "每秒帧数 N", self.fps_spin)

        self.interval_spin = QSpinBox(self)
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(5)
        self._add_mode_row(form, "interval", "间隔秒数 N", self.interval_spin)

        self.total_spin = QSpinBox(self)
        self.total_spin.setRange(1, 1_000_000)
        self.total_spin.setValue(100)
        self._add_mode_row(form, "total", "总帧数 M", self.total_spin)

        self.start_edit = QLineEdit("00:00:00", self)
        self.start_edit.setPlaceholderText("HH:MM:SS 或秒数")
        self._add_mode_row(form, "start", "起始时间", self.start_edit)

        self.end_edit = QLineEdit("00:00:10", self)
        self.end_edit.setPlaceholderText("HH:MM:SS 或秒数")
        self._add_mode_row(form, "end", "结束时间", self.end_edit)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["jpg", "png", "webp"])
        form.addRow("图片格式", self.format_combo)

        self.quality_spin = QSpinBox(self)
        self.quality_spin.setRange(1, 31)
        self.quality_spin.setValue(2)
        self.quality_spin.setToolTip("JPG: -q:v，1 质量最高；PNG/WebP 会自动映射为对应质量参数。")
        form.addRow("质量参数", self.quality_spin)

        self.output_edit = QLineEdit(str(Path.cwd() / "frames_output"), self)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.choose_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, stretch=1)
        output_row.addWidget(browse_btn)
        form.addRow("输出文件夹", output_row)

        self.template_edit = QLineEdit("%06d", self)
        self.template_edit.setPlaceholderText("例如 {video}_{index:06d}")
        self.template_edit.setToolTip(
            "支持 {video}, {date}, {time}, {datetime}, {index}, {index:06d}，也兼容 FFmpeg 的 %06d 写法。"
        )
        form.addRow("文件名模板", self.template_edit)

        layout.addWidget(form_holder)
        layout.addStretch(1)
        return panel

    def _build_bottom_panel(self) -> QWidget:
        """底部日志、进度和控制按钮。"""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        log_title = QLabel("运行日志")
        log_title.setObjectName("SectionTitle")
        layout.addWidget(log_title)

        self.log_edit = QPlainTextEdit(self)
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(4000)
        layout.addWidget(self.log_edit, stretch=1)

        control_row = QHBoxLayout()
        self.file_progress = QProgressBar(self)
        self.file_progress.setFormat("当前文件 %p%")
        self.total_progress = QProgressBar(self)
        self.total_progress.setFormat("总进度 %p%")
        self.start_btn = QPushButton("开始")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self.start_extract)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.controller.cancel_extract)

        control_row.addWidget(self.file_progress, stretch=2)
        control_row.addWidget(self.total_progress, stretch=2)
        control_row.addWidget(self.start_btn)
        control_row.addWidget(self.cancel_btn)
        layout.addLayout(control_row)
        return panel

    def _connect_controller(self) -> None:
        """连接 Controller 发出的状态信号。"""
        self.controller.queue_changed.connect(self.render_video_queue)
        self.controller.preview_changed.connect(self.render_preview)
        self.controller.log.connect(self.append_log)
        self.controller.status.connect(self.statusBar().showMessage)
        self.controller.file_progress.connect(self.file_progress.setValue)
        self.controller.total_progress.connect(self.total_progress.setValue)
        self.controller.task_running_changed.connect(self.set_task_running)
        self.controller.error.connect(self.show_error)

    def _restore_persisted_state(self) -> None:
        """恢复窗口几何信息和上次配置。"""
        geometry = self.controller.load_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        self.apply_config(self.controller.load_config())

    def _load_style(self) -> None:
        """加载深色 QSS 主题。"""
        qss_path = Path(__file__).with_name("styles.qss")
        if qss_path.exists():
            QApplication.instance().setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _check_ffmpeg_on_startup(self) -> None:
        """启动时检测 FFmpeg，提前给出清晰提示。"""
        try:
            ensure_ffmpeg()
            self.append_log("FFmpeg 检测通过。")
        except RuntimeError as exc:
            self.append_log(str(exc))
            QMessageBox.warning(self, "FFmpeg 未就绪", str(exc))

    def _add_mode_row(self, form: QFormLayout, key: str, label: str, field: QWidget) -> None:
        """添加会随提取模式切换显隐的表单行。"""
        label_widget = QLabel(label, self)
        form.addRow(label_widget, field)
        self.mode_rows[key] = (label_widget, field)

    def update_mode_fields(self, mode: str) -> None:
        """不同提取模式只展示有效配置项。"""
        visible_keys = {
            MODE_FPS: {"fps"},
            MODE_INTERVAL: {"interval"},
            MODE_TOTAL: {"total"},
            MODE_RANGE: {"start", "end", "fps"},
        }.get(mode, set())

        for key, widgets in self.mode_rows.items():
            is_visible = key in visible_keys
            for widget in widgets:
                widget.setVisible(is_visible)

    def open_files(self) -> None:
        """弹出文件选择器添加视频。"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            str(Path.home()),
            "Video Files (*.mp4 *.mov *.mkv *.avi *.wmv *.flv *.webm *.m4v *.mpeg *.mpg *.ts);;All Files (*)",
        )
        self.controller.add_paths([Path(file) for file in files])

    def choose_output_dir(self) -> None:
        """选择输出目录。"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_edit.text())
        if directory:
            self.output_edit.setText(directory)

    def remove_selected(self) -> None:
        """从队列中移除选中的视频。"""
        rows = [index.row() for index in self.video_list.selectedIndexes()]
        self.controller.remove_rows(rows)

    def start_extract(self) -> None:
        """采集表单配置并交给 Controller 启动任务。"""
        config = self.collect_config()
        self.controller.start_extract(config)

    def render_video_queue(self, videos: list[str]) -> None:
        """渲染视频队列。"""
        current_row = self.video_list.currentRow()
        self.video_list.blockSignals(True)
        self.video_list.clear()
        self.video_list.addItems(videos)
        self.video_list.blockSignals(False)

        if videos:
            next_row = min(max(current_row, 0), len(videos) - 1)
            self.video_list.setCurrentRow(next_row)
            self.controller.update_preview(next_row)
        else:
            self.controller.update_preview(-1)

    def render_preview(self, text: str, end_time: str) -> None:
        """渲染视频信息预览。"""
        self.info_label.setText(text)
        if end_time:
            self.end_edit.setText(end_time)

    def set_task_running(self, running: bool) -> None:
        """切换任务运行状态。"""
        self.start_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)

    def show_error(self, title: str, message: str) -> None:
        """展示错误信息。"""
        self.append_log(f"{title}: {message}")
        QMessageBox.warning(self, title, message)

    def append_log(self, text: str) -> None:
        """追加日志并自动滚动到底部。"""
        self.log_edit.appendPlainText(text)
        scrollbar = self.log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def collect_config(self) -> AppConfig:
        """从表单采集当前配置。"""
        return AppConfig(
            mode=self.mode_combo.currentText(),
            fps=self.fps_spin.value(),
            interval_seconds=self.interval_spin.value(),
            total_frames=self.total_spin.value(),
            start_time=self.start_edit.text().strip(),
            end_time=self.end_edit.text().strip(),
            image_format=self.format_combo.currentText(),
            quality=self.quality_spin.value(),
            output_dir=Path(self.output_edit.text()).expanduser(),
            filename_template=self.template_edit.text().strip(),
        )

    def apply_config(self, config: AppConfig) -> None:
        """把配置应用到表单控件。"""
        mode_index = self.mode_combo.findText(config.mode)
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)
        self.fps_spin.setValue(config.fps)
        self.interval_spin.setValue(config.interval_seconds)
        self.total_spin.setValue(config.total_frames)
        self.start_edit.setText(config.start_time)
        self.end_edit.setText(config.end_time)

        format_index = self.format_combo.findText(config.image_format)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
        self.quality_spin.setValue(config.quality)
        self.output_edit.setText(str(config.output_dir))
        self.template_edit.setText(config.filename_template)
        self.update_mode_fields(self.mode_combo.currentText())

    def show_about(self) -> None:
        """关于对话框。"""
        QMessageBox.about(
            self,
            "关于",
            "Video Frame Exporter\n\n基于 PySide6 + FFmpeg 的批量视频转图片工具。",
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """允许拖拽文件/文件夹进入。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """处理拖拽的视频文件或目录。"""
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.controller.add_paths(paths)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭时保存配置。"""
        self.controller.save_config(self.collect_config())
        self.controller.save_geometry(self.saveGeometry())
        super().closeEvent(event)
