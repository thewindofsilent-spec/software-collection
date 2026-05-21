"""MVC 中的 Controller 层。

Controller 连接 View、Model 和后台 Worker，负责业务调度和线程生命周期。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from models import AppConfig, SettingsRepository, VideoQueueModel
from utils import format_video_info, probe_video, seconds_to_hms
from worker import FrameExtractWorker


class MainController(QObject):
    """主控制器。"""

    queue_changed = Signal(list)
    preview_changed = Signal(str, str)
    log = Signal(str)
    status = Signal(str)
    file_progress = Signal(int)
    total_progress = Signal(int)
    task_running_changed = Signal(bool)
    error = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.queue = VideoQueueModel()
        self.settings_repository = SettingsRepository()
        self.thread: QThread | None = None
        self.worker: FrameExtractWorker | None = None

    @property
    def is_running(self) -> bool:
        """当前是否有任务在执行。"""
        return self.thread is not None

    def load_config(self) -> AppConfig:
        """读取配置存档。"""
        return self.settings_repository.load_config()

    def save_config(self, config: AppConfig) -> None:
        """保存配置存档。"""
        self.settings_repository.save_config(config)

    def load_geometry(self):
        """读取窗口几何信息。"""
        return self.settings_repository.load_geometry()

    def save_geometry(self, geometry) -> None:
        """保存窗口几何信息。"""
        self.settings_repository.save_geometry(geometry)

    def add_paths(self, paths: list[Path]) -> None:
        """添加视频到队列。"""
        added = self.queue.add_paths(paths)
        self.queue_changed.emit([str(video) for video in self.queue.videos])
        self.log.emit(f"已添加 {len(added)} 个视频。")
        self.status.emit(f"队列中共有 {len(self.queue)} 个视频。")

    def remove_rows(self, rows: list[int]) -> None:
        """删除队列中的指定行。"""
        self.queue.remove_rows(rows)
        self.queue_changed.emit([str(video) for video in self.queue.videos])
        self.status.emit(f"队列中共有 {len(self.queue)} 个视频。")

    def update_preview(self, row: int) -> None:
        """读取指定视频的预览信息。"""
        video = self.queue.video_at(row)
        if video is None:
            self.preview_changed.emit("暂无视频。\n\n支持拖拽文件或文件夹批量添加。", "")
            return

        try:
            info = probe_video(video)
            end_time = seconds_to_hms(info.duration) if info.duration > 0 else ""
            self.preview_changed.emit(format_video_info(info), end_time)
        except Exception as exc:
            self.preview_changed.emit(f"读取视频信息失败:\n{exc}", "")

    def start_extract(self, config: AppConfig) -> None:
        """启动后台提帧任务。"""
        if self.is_running:
            return
        if len(self.queue) == 0:
            self.error.emit("没有任务", "请先添加视频文件。")
            return
        if not config.filename_template.strip():
            self.error.emit("参数错误", "文件名模板不能为空。")
            return

        self.save_config(config)
        self.file_progress.emit(0)
        self.total_progress.emit(0)
        self.task_running_changed.emit(True)

        self.thread = QThread(self)
        self.worker = FrameExtractWorker(self.queue.videos, config.to_extract_settings())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.log)
        self.worker.file_started.connect(lambda path: self.status.emit(f"正在处理: {path}"))
        self.worker.file_progress.connect(self.file_progress)
        self.worker.total_progress.connect(self.total_progress)
        self.worker.failed.connect(lambda message: self.error.emit("任务失败", message))
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def cancel_extract(self) -> None:
        """取消后台任务。"""
        if self.worker:
            self.log.emit("正在请求取消任务...")
            self.worker.cancel()

    def _on_worker_finished(self) -> None:
        """后台任务结束后的收尾。"""
        self.task_running_changed.emit(False)
        self.status.emit("任务结束。")
        self.thread = None
        self.worker = None
