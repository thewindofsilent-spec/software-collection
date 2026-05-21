"""MVC 中的 Model 层。

Model 只保存应用状态和配置，不直接操作界面，也不启动 FFmpeg。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings

from utils import collect_video_files


MODE_FPS = "每秒提取 N 帧"
MODE_INTERVAL = "每隔 N 秒提取 1 帧"
MODE_TOTAL = "提取总共 M 帧"
MODE_RANGE = "指定起止时间"
EXTRACT_MODES = [MODE_FPS, MODE_INTERVAL, MODE_TOTAL, MODE_RANGE]


@dataclass(frozen=True)
class ExtractSettings:
    """一次提帧任务所需的完整参数。"""

    mode: str
    fps: int
    interval_seconds: int
    total_frames: int
    start_time: str
    end_time: str
    image_format: str
    quality: int
    output_dir: Path
    filename_template: str


@dataclass
class AppConfig:
    """可持久化的界面配置。"""

    mode: str = MODE_FPS
    fps: int = 1
    interval_seconds: int = 5
    total_frames: int = 100
    start_time: str = "00:00:00"
    end_time: str = "00:00:10"
    image_format: str = "jpg"
    quality: int = 2
    output_dir: Path = Path.cwd() / "frames_output"
    filename_template: str = "%06d"

    def to_extract_settings(self) -> ExtractSettings:
        """转换为 Worker 使用的不可变任务配置。"""
        return ExtractSettings(
            mode=self.mode,
            fps=self.fps,
            interval_seconds=self.interval_seconds,
            total_frames=self.total_frames,
            start_time=self.start_time,
            end_time=self.end_time,
            image_format=self.image_format,
            quality=self.quality,
            output_dir=self.output_dir.expanduser().resolve(),
            filename_template=self.filename_template,
        )


class VideoQueueModel:
    """视频队列模型。"""

    def __init__(self) -> None:
        self._videos: list[Path] = []

    @property
    def videos(self) -> list[Path]:
        """返回队列副本，避免外部直接修改内部状态。"""
        return self._videos.copy()

    def __len__(self) -> int:
        return len(self._videos)

    def add_paths(self, paths: list[Path]) -> list[Path]:
        """添加文件或目录，返回本次实际新增的视频。"""
        candidates = collect_video_files(paths)
        existing = set(self._videos)
        added = [video for video in candidates if video not in existing]
        self._videos.extend(added)
        return added

    def remove_rows(self, rows: list[int]) -> None:
        """按行号删除视频。"""
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._videos):
                self._videos.pop(row)

    def video_at(self, row: int) -> Path | None:
        """读取指定行的视频路径。"""
        if 0 <= row < len(self._videos):
            return self._videos[row]
        return None


class SettingsRepository:
    """配置存档仓库，封装 QSettings。"""

    def __init__(self) -> None:
        self._settings = QSettings("CommercialTools", "VideoFrameExporter")

    def load_config(self) -> AppConfig:
        """加载上次配置。"""
        return AppConfig(
            mode=str(self._settings.value("extract/mode", MODE_FPS)),
            fps=self._read_int("extract/fps", 1),
            interval_seconds=self._read_int("extract/interval_seconds", 5),
            total_frames=self._read_int("extract/total_frames", 100),
            start_time=str(self._settings.value("extract/start_time", "00:00:00")),
            end_time=str(self._settings.value("extract/end_time", "00:00:10")),
            image_format=str(self._settings.value("output/format", "jpg")),
            quality=self._read_int("output/quality", 2),
            output_dir=Path(str(self._settings.value("output/directory", Path.cwd() / "frames_output"))),
            filename_template=str(self._settings.value("output/template", "%06d")),
        )

    def save_config(self, config: AppConfig) -> None:
        """保存当前配置。"""
        self._settings.setValue("extract/mode", config.mode)
        self._settings.setValue("extract/fps", config.fps)
        self._settings.setValue("extract/interval_seconds", config.interval_seconds)
        self._settings.setValue("extract/total_frames", config.total_frames)
        self._settings.setValue("extract/start_time", config.start_time)
        self._settings.setValue("extract/end_time", config.end_time)
        self._settings.setValue("output/format", config.image_format)
        self._settings.setValue("output/quality", config.quality)
        self._settings.setValue("output/directory", str(config.output_dir))
        self._settings.setValue("output/template", config.filename_template)
        self._settings.sync()

    def load_geometry(self):
        """加载窗口几何信息。"""
        return self._settings.value("window/geometry")

    def save_geometry(self, geometry) -> None:
        """保存窗口几何信息。"""
        self._settings.setValue("window/geometry", geometry)
        self._settings.sync()

    def _read_int(self, key: str, default: int) -> int:
        value = self._settings.value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
