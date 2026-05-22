from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Sequence, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal


BackgroundMethod = Literal["average_background", "gmm", "mog2", "knn"]


class BackgroundExtractorError(RuntimeError):
    """Raised when background extraction fails."""


@dataclass(frozen=True)
class BackgroundExtractionResult:
    """Result of a background extraction run.

    Attributes:
        background: Estimated background image in BGR format.
        foreground_masks: One uint8 mask per input image. Foreground is 255.
        foregrounds: One BGR foreground image per input image.
    """

    background: np.ndarray
    foreground_masks: List[np.ndarray]
    foregrounds: List[np.ndarray]


class BackgroundExtractor(QObject):
    """Extract background and foreground masks from multiple image paths.

    Designed for QThread usage:

        extractor = BackgroundExtractor()
        extractor.progressChanged.connect(progress_bar.setValue)
        result = extractor.extract(paths, method="average_background")

    Signals:
        started(total): emitted before processing begins.
        progressChanged(percent): integer 0-100 for progress bars.
        progressMessage(message): human-readable current stage.
        frameProcessed(index, total): emitted after each input frame.
        finished(result): emitted with BackgroundExtractionResult.
        failed(message): emitted when an exception occurs.
    """

    started = Signal(int)
    progressChanged = Signal(int)
    progressMessage = Signal(str)
    frameProcessed = Signal(int, int)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def extract(
        self,
        image_paths: Sequence[str | Path],
        *,
        method: BackgroundMethod = "average_background",
        threshold: int = 25,
        history: int = 500,
        learning_rate: float = -1.0,
        detect_shadows: bool = True,
        resize_to_first: bool = True,
    ) -> BackgroundExtractionResult:
        """Run background extraction.

        Args:
            image_paths: Ordered image file paths.
            method: average_background, gmm/mog2, or knn.
            threshold: Foreground threshold. For MOG2 this maps to varThreshold;
                for KNN this maps to dist2Threshold via threshold ** 2.
            history: Background model history for GMM/KNN.
            learning_rate: OpenCV model learning rate. -1 lets OpenCV decide.
            detect_shadows: Whether OpenCV subtractors mark shadows.
            resize_to_first: Resize later frames to the first frame size when
                dimensions differ.

        Returns:
            BackgroundExtractionResult containing BGR background, masks, and foregrounds.
        """

        self._cancelled = False
        paths = [Path(path) for path in image_paths]
        if not paths:
            raise BackgroundExtractorError("图片路径列表不能为空")

        total = len(paths)
        self.started.emit(total)
        self.progressChanged.emit(0)

        try:
            frames = self._load_frames(paths, resize_to_first=resize_to_first)
            normalized_method = self._normalize_method(method)

            if normalized_method == "average_background":
                result = self.average_background(frames, threshold=threshold)
            elif normalized_method == "mog2":
                result = self.create_gmm_background(
                    frames,
                    threshold=threshold,
                    history=history,
                    learning_rate=learning_rate,
                    detect_shadows=detect_shadows,
                )
            elif normalized_method == "knn":
                result = self.knn(
                    frames,
                    threshold=threshold,
                    history=history,
                    learning_rate=learning_rate,
                    detect_shadows=detect_shadows,
                )
            else:
                raise BackgroundExtractorError(f"不支持的背景提取方法：{method}")

            self.progressChanged.emit(100)
            self.finished.emit(result)
            return result
        except Exception as exc:
            message = str(exc)
            self.failed.emit(message)
            raise

    def average_background(
        self,
        frames: Sequence[np.ndarray],
        *,
        threshold: int = 25,
    ) -> BackgroundExtractionResult:
        """Estimate background by averaging all frames, then threshold absdiff."""

        if not frames:
            raise BackgroundExtractorError("图像帧不能为空")

        self.progressMessage.emit("正在生成平均背景")
        accumulator = np.zeros_like(frames[0], dtype=np.float32)
        total = len(frames)

        for index, frame in enumerate(frames, start=1):
            self._raise_if_cancelled()
            accumulator += frame.astype(np.float32)
            self._emit_stage_progress(index, total, start=45, end=70)

        background = np.clip(accumulator / total, 0, 255).astype(np.uint8)
        masks, foregrounds = self._build_masks_from_background(
            frames,
            background,
            threshold=threshold,
            progress_start=70,
            progress_end=98,
        )
        return BackgroundExtractionResult(background=background, foreground_masks=masks, foregrounds=foregrounds)

    def create_gmm_background(
        self,
        frames: Sequence[np.ndarray],
        *,
        threshold: int = 25,
        history: int = 500,
        learning_rate: float = -1.0,
        detect_shadows: bool = True,
    ) -> BackgroundExtractionResult:
        """Estimate background using OpenCV MOG2/GMM background subtractor."""

        if not frames:
            raise BackgroundExtractorError("图像帧不能为空")

        subtractor = cv2.createBackgroundSubtractorMOG2(
            history=max(1, int(history)),
            varThreshold=max(0, int(threshold)),
            detectShadows=detect_shadows,
        )
        masks = self._train_subtractor(
            frames,
            subtractor,
            learning_rate=learning_rate,
            message="正在训练 GMM 背景模型",
        )
        background = subtractor.getBackgroundImage()
        if background is None:
            background = self._median_background(frames)
        foregrounds = [cv2.bitwise_and(frame, frame, mask=mask) for frame, mask in zip(frames, masks)]
        return BackgroundExtractionResult(background=background, foreground_masks=masks, foregrounds=foregrounds)

    def knn(
        self,
        frames: Sequence[np.ndarray],
        *,
        threshold: int = 25,
        history: int = 500,
        learning_rate: float = -1.0,
        detect_shadows: bool = True,
    ) -> BackgroundExtractionResult:
        """Estimate background using OpenCV KNN background subtractor."""

        if not frames:
            raise BackgroundExtractorError("图像帧不能为空")

        subtractor = cv2.createBackgroundSubtractorKNN(
            history=max(1, int(history)),
            dist2Threshold=float(max(0, int(threshold)) ** 2),
            detectShadows=detect_shadows,
        )
        masks = self._train_subtractor(
            frames,
            subtractor,
            learning_rate=learning_rate,
            message="正在训练 KNN 背景模型",
        )
        background = subtractor.getBackgroundImage()
        if background is None:
            background = self._median_background(frames)
        foregrounds = [cv2.bitwise_and(frame, frame, mask=mask) for frame, mask in zip(frames, masks)]
        return BackgroundExtractionResult(background=background, foreground_masks=masks, foregrounds=foregrounds)

    def _load_frames(self, paths: Sequence[Path], *, resize_to_first: bool) -> List[np.ndarray]:
        self.progressMessage.emit("正在加载图片")
        frames: List[np.ndarray] = []
        target_size: Optional[Tuple[int, int]] = None
        total = len(paths)

        for index, path in enumerate(paths, start=1):
            self._raise_if_cancelled()
            frame = self._read_image(path)
            if target_size is None:
                target_size = (frame.shape[1], frame.shape[0])
            elif (frame.shape[1], frame.shape[0]) != target_size:
                if not resize_to_first:
                    raise BackgroundExtractorError(
                        f"图像尺寸不一致：{path} 的尺寸为 {(frame.shape[1], frame.shape[0])}，"
                        f"期望尺寸为 {target_size}"
                    )
                frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

            frames.append(frame)
            self.frameProcessed.emit(index, total)
            self._emit_stage_progress(index, total, start=0, end=45)

        return frames

    def _train_subtractor(
        self,
        frames: Sequence[np.ndarray],
        subtractor: cv2.BackgroundSubtractor,
        *,
        learning_rate: float,
        message: str,
    ) -> List[np.ndarray]:
        self.progressMessage.emit(message)
        masks: List[np.ndarray] = []
        total = len(frames)

        for index, frame in enumerate(frames, start=1):
            self._raise_if_cancelled()
            mask = subtractor.apply(frame, learningRate=float(learning_rate))
            mask = self._clean_mask(mask)
            masks.append(mask)
            self.frameProcessed.emit(index, total)
            self._emit_stage_progress(index, total, start=45, end=98)

        return masks

    def _build_masks_from_background(
        self,
        frames: Sequence[np.ndarray],
        background: np.ndarray,
        *,
        threshold: int,
        progress_start: int,
        progress_end: int,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        self.progressMessage.emit("正在提取前景掩码")
        masks: List[np.ndarray] = []
        foregrounds: List[np.ndarray] = []
        total = len(frames)

        for index, frame in enumerate(frames, start=1):
            self._raise_if_cancelled()
            diff = cv2.absdiff(frame, background)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, max(0, int(threshold)), 255, cv2.THRESH_BINARY)
            mask = self._clean_mask(mask)
            foreground = cv2.bitwise_and(frame, frame, mask=mask)
            masks.append(mask)
            foregrounds.append(foreground)
            self.frameProcessed.emit(index, total)
            self._emit_stage_progress(index, total, start=progress_start, end=progress_end)

        return masks, foregrounds

    @staticmethod
    def _read_image(path: Path) -> np.ndarray:
        if not path.exists():
            raise BackgroundExtractorError(f"找不到图片：{path}")

        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            raise BackgroundExtractorError(f"图片为空或无法读取：{path}")

        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise BackgroundExtractorError(f"图片解码失败：{path}")

        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 3:
            return image
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        raise BackgroundExtractorError(f"不支持的图像尺寸或通道：{path}，{image.shape}")

    @staticmethod
    def _clean_mask(mask: np.ndarray) -> np.ndarray:
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        return binary

    @staticmethod
    def _median_background(frames: Sequence[np.ndarray]) -> np.ndarray:
        stacked = np.stack(frames, axis=0)
        return np.median(stacked, axis=0).astype(np.uint8)

    @staticmethod
    def _normalize_method(method: str) -> str:
        normalized = method.strip().lower()
        if normalized in {"average", "avg", "average_background", "平均法"}:
            return "average_background"
        if normalized in {"gmm", "mog2", "create_gmm_background"}:
            return "mog2"
        if normalized == "knn":
            return "knn"
        return normalized

    def _emit_stage_progress(self, index: int, total: int, *, start: int, end: int) -> None:
        if total <= 0:
            return
        span = max(0, end - start)
        percent = start + int(span * index / total)
        self.progressChanged.emit(max(0, min(100, percent)))

    def _raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise BackgroundExtractorError("背景提取已取消")
