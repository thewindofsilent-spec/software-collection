"""后台 FFmpeg Worker。

QThread 负责线程，FrameExtractWorker 作为 QObject 在该线程内运行。
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from models import MODE_FPS, MODE_INTERVAL, MODE_RANGE, MODE_TOTAL, ExtractSettings
from utils import ensure_ffmpeg, hms_to_seconds, parse_ffmpeg_time, probe_video, sanitize_filename, unique_output_dir


class FrameExtractWorker(QObject):
    """在后台线程中批量调用 FFmpeg 提取图片。"""

    log = Signal(str)
    file_started = Signal(str)
    file_progress = Signal(int)
    total_progress = Signal(int)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, videos: list[Path], settings: ExtractSettings) -> None:
        super().__init__()
        self.videos = videos
        self.settings = settings
        self._cancelled = False
        self._process: subprocess.Popen[str] | None = None

    @Slot()
    def run(self) -> None:
        """批量执行提帧任务。"""
        try:
            ffmpeg, ffprobe = ensure_ffmpeg()
            if not self.videos:
                raise RuntimeError("请先添加至少一个视频文件。")

            self.settings.output_dir.mkdir(parents=True, exist_ok=True)
            total_count = len(self.videos)

            for index, video in enumerate(self.videos, start=1):
                if self._cancelled:
                    self.log.emit("任务已取消。")
                    break

                self.file_started.emit(str(video))
                self.file_progress.emit(0)
                info = probe_video(video, ffprobe)
                output_dir = unique_output_dir(self.settings.output_dir, video)
                output_dir.mkdir(parents=True, exist_ok=True)

                cmd, progress_duration = self._build_command(ffmpeg, video, info.duration, output_dir)
                self.log.emit(f"开始处理 ({index}/{total_count}): {video.name}")
                self.log.emit("输出目录: " + str(output_dir))

                self._run_ffmpeg(cmd, progress_duration)
                self._process = None

                if self._cancelled:
                    self.log.emit(f"已停止: {video.name}")
                    break

                self.file_progress.emit(100)
                self.total_progress.emit(round(index / total_count * 100))
                self.log.emit(f"完成: {video.name}")

            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        """请求取消当前任务。"""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _run_ffmpeg(self, cmd: list[str], progress_duration: float) -> None:
        """运行 FFmpeg 并实时解析 stderr 进度。"""
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert self._process.stderr is not None
        for line in self._process.stderr:
            text = line.strip()
            if text:
                self.log.emit(text)

            current = parse_ffmpeg_time(text)
            if current is not None and progress_duration > 0:
                percent = max(0, min(99, round(current / progress_duration * 100)))
                self.file_progress.emit(percent)

            if self._cancelled and self._process.poll() is None:
                self._process.terminate()

        return_code = self._process.wait()
        if self._cancelled:
            return
        if return_code != 0:
            raise RuntimeError(f"FFmpeg 执行失败，退出码: {return_code}")

    def _build_command(
        self,
        ffmpeg: str,
        video: Path,
        duration: float,
        output_dir: Path,
    ) -> tuple[list[str], float]:
        """根据模式构造 FFmpeg 参数。"""
        output_pattern = self._output_pattern(output_dir, video)
        cmd = [ffmpeg, "-hide_banner", "-y"]

        start_seconds = hms_to_seconds(self.settings.start_time)
        end_seconds = hms_to_seconds(self.settings.end_time)
        progress_duration = duration

        if self.settings.mode == MODE_RANGE:
            if end_seconds <= start_seconds:
                raise RuntimeError("结束时间必须大于起始时间。")
            cmd.extend(["-ss", f"{start_seconds:.3f}", "-to", f"{end_seconds:.3f}"])
            progress_duration = max(0.1, end_seconds - start_seconds)
        elif start_seconds > 0:
            cmd.extend(["-ss", f"{start_seconds:.3f}"])
            progress_duration = max(0.1, duration - start_seconds)

        cmd.extend(["-i", str(video)])

        vf = self._video_filter(duration=duration, start_seconds=start_seconds, end_seconds=end_seconds)
        if vf:
            cmd.extend(["-vf", vf])

        cmd.extend(self._quality_args())
        if self.settings.mode == MODE_TOTAL:
            cmd.extend(["-frames:v", str(self.settings.total_frames)])
        cmd.extend(["-vsync", "0", str(output_pattern)])
        return cmd, progress_duration

    def _video_filter(self, duration: float, start_seconds: float, end_seconds: float) -> str:
        """生成提帧滤镜表达式。"""
        mode = self.settings.mode
        if mode == MODE_FPS:
            return f"fps={self.settings.fps}"
        if mode == MODE_INTERVAL:
            return f"fps=1/{self.settings.interval_seconds}"
        if mode == MODE_TOTAL:
            effective_duration = max(0.1, duration - start_seconds)
            fps = max(0.0001, self.settings.total_frames / effective_duration)
            return f"fps={fps:.6f}"
        if mode == MODE_RANGE:
            effective_duration = max(0.1, end_seconds - start_seconds)
            fps = max(0.0001, self.settings.fps)
            return f"fps={fps},trim=duration={effective_duration:.3f}"
        return ""

    def _quality_args(self) -> list[str]:
        """按输出格式生成质量参数。"""
        fmt = self.settings.image_format.lower()
        quality = self.settings.quality
        if fmt in {"jpg", "jpeg"}:
            return ["-q:v", str(max(1, min(31, quality)))]
        if fmt == "png":
            compression = round((max(1, min(31, quality)) - 1) / 30 * 9)
            return ["-compression_level", str(compression)]
        if fmt == "webp":
            webp_quality = round(100 - (max(1, min(31, quality)) - 1) / 30 * 80)
            return ["-q:v", str(webp_quality)]
        return []

    def _output_pattern(self, output_dir: Path, video: Path) -> Path:
        """生成 FFmpeg 序列帧输出路径。"""
        template = self.settings.filename_template.strip() or "%06d"
        suffix = "." + self.settings.image_format.lower().lstrip(".")

        template_path = Path(template)
        if template_path.suffix:
            template = str(template_path.with_suffix(""))

        template = self._expand_filename_template(template, video)
        if "%" not in template:
            template = f"{template}_%06d"
        template += suffix
        return output_dir / template

    def _expand_filename_template(self, template: str, video: Path) -> str:
        """把用户友好的模板变量转换为 FFmpeg 可识别的输出模板。"""
        now = datetime.now()
        replacements = {
            "{video}": sanitize_filename(video.stem),
            "{date}": now.strftime("%Y%m%d"),
            "{time}": now.strftime("%H%M%S"),
            "{datetime}": now.strftime("%Y%m%d_%H%M%S"),
            "{index}": "%06d",
        }
        for token, value in replacements.items():
            template = template.replace(token, value)

        for width in range(1, 13):
            template = template.replace(f"{{index:{width:02d}d}}", f"%0{width}d")
            template = template.replace(f"{{index:{width}d}}", f"%0{width}d")

        return sanitize_filename(template)
