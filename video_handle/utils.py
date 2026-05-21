"""FFmpeg/路径/时间等通用工具函数。

本模块刻意不依赖 UI，便于单元测试和复用。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ts",
}

TIME_RE = re.compile(r"time=(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d+)?)")


@dataclass(frozen=True)
class VideoInfo:
    """视频元信息。"""

    path: Path
    duration: float
    width: int
    height: int
    fps: float
    codec: str


def find_executable(name: str) -> str | None:
    """查找可执行文件，返回绝对路径或 None。"""
    return shutil.which(name)


def ensure_ffmpeg() -> tuple[str, str]:
    """检测 FFmpeg/FFprobe 是否存在。

    Raises:
        RuntimeError: 未找到 ffmpeg 或 ffprobe。
    """
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "未检测到 FFmpeg/FFprobe。请先安装 FFmpeg，并确保 ffmpeg 与 ffprobe 已加入 PATH。"
        )
    return ffmpeg, ffprobe


def is_video_file(path: Path) -> bool:
    """根据扩展名判断是否为常见视频文件。"""
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def unique_output_dir(base_dir: Path, video_path: Path) -> Path:
    """为每个视频创建不冲突的输出子目录。"""
    stem = sanitize_filename(video_path.stem)
    candidate = base_dir / stem
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        next_candidate = base_dir / f"{stem}_{index}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def sanitize_filename(name: str) -> str:
    """移除 Windows/macOS/Linux 不友好的文件名字符。"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip()
    return cleaned or "video"


def seconds_to_hms(seconds: float) -> str:
    """秒数转 HH:MM:SS.mmm。"""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def hms_to_seconds(value: str) -> float:
    """解析 HH:MM:SS(.ms) 或纯秒数字符串。"""
    text = value.strip()
    if not text:
        return 0.0
    if ":" not in text:
        return max(0.0, float(text))

    parts = text.split(":")
    if len(parts) != 3:
        raise ValueError("时间格式应为 HH:MM:SS，例如 00:01:30")
    hours, minutes, seconds = parts
    return max(0.0, int(hours) * 3600 + int(minutes) * 60 + float(seconds))


def parse_ffmpeg_time(line: str) -> float | None:
    """从 FFmpeg stderr 行中解析当前处理时间。"""
    match = TIME_RE.search(line)
    if not match:
        return None
    return hms_to_seconds(match.group("time"))


def probe_video(video_path: Path, ffprobe: str | None = None) -> VideoInfo:
    """调用 ffprobe 获取视频时长、分辨率、帧率和编码信息。"""
    if ffprobe is None:
        _, ffprobe = ensure_ffmpeg()

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name,avg_frame_rate:format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"无法读取视频信息: {video_path}")

    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError(f"未找到视频流: {video_path}")

    stream = streams[0]
    duration = float((data.get("format") or {}).get("duration") or 0)
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    codec = stream.get("codec_name") or "unknown"
    fps = parse_fraction(stream.get("avg_frame_rate") or "0/1")
    return VideoInfo(path=video_path, duration=duration, width=width, height=height, fps=fps, codec=codec)


def parse_fraction(value: str) -> float:
    """解析 FFprobe 的 30000/1001 这类帧率表达。"""
    try:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return 0.0
        return float(numerator) / denominator_value
    except Exception:
        try:
            return float(value)
        except ValueError:
            return 0.0


def format_video_info(info: VideoInfo) -> str:
    """格式化视频信息，供 UI 展示。"""
    return (
        f"文件: {info.path.name}\n"
        f"时长: {seconds_to_hms(info.duration)}\n"
        f"分辨率: {info.width} x {info.height}\n"
        f"帧率: {info.fps:.3f} fps\n"
        f"编码: {info.codec}"
    )


def collect_video_files(paths: Iterable[Path]) -> list[Path]:
    """从文件/目录列表中收集可处理的视频文件。"""
    videos: list[Path] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        if is_video_file(resolved):
            videos.append(resolved)
        elif resolved.is_dir():
            videos.extend(p for p in resolved.rglob("*") if is_video_file(p))
    return sorted(dict.fromkeys(videos))
