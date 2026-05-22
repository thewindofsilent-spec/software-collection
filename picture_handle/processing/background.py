from __future__ import annotations

from typing import ClassVar, Iterable, Optional

import cv2
import numpy as np

from processing.operation import Operation, OperationError, ParameterDict


class BackgroundSubtractor(Operation):
    """Background modeling / foreground extraction operation.

    Supported methods:
        - Average: builds a background image from frames and thresholds absdiff.
        - MOG2: OpenCV createBackgroundSubtractorMOG2.
        - KNN: OpenCV createBackgroundSubtractorKNN.
    """

    operation_type: ClassVar[str] = "BackgroundSubtractor"
    name: ClassVar[str] = "背景提取"
    default_parameters: ClassVar[ParameterDict] = {
        "method": "MOG2",
        "history": 200,
        "threshold": 25,
        "learning_rate": -1.0,
        "detect_shadows": True,
        "output": "前景",
    }
    parameter_specs: ClassVar[dict] = {
        "method": {"type": "choice", "label": "建模方法", "options": ["平均法", "MOG2", "KNN"]},
        "history": {"type": "int", "label": "历史帧数", "min": 1, "max": 10000},
        "threshold": {"type": "int", "label": "阈值", "min": 0, "max": 255},
        "learning_rate": {"type": "float", "label": "学习率", "min": -1.0, "max": 1.0, "step": 0.01, "decimals": 3},
        "detect_shadows": {"type": "bool", "label": "检测阴影"},
        "output": {"type": "choice", "label": "输出", "options": ["前景", "掩码", "背景"]},
    }

    def __init__(self, parameters: Optional[dict] = None) -> None:
        super().__init__(parameters)
        self._average_background: Optional[np.ndarray] = None
        self._subtractor: Optional[cv2.BackgroundSubtractor] = None
        self._subtractor_signature: Optional[tuple] = None

    def set_background_frames(self, frames: Iterable[np.ndarray]) -> None:
        prepared = [self._as_bgr(frame).astype(np.float32) for frame in frames if frame is not None and frame.size]
        if not prepared:
            raise OperationError("背景提取：没有可用的背景帧")
        self._average_background = np.mean(prepared, axis=0).astype(np.uint8)

    def reset_model(self) -> None:
        self._subtractor = None
        self._subtractor_signature = None
        self._average_background = None

    def apply(self, mat: np.ndarray) -> np.ndarray:
        if mat is None or mat.size == 0:
            raise OperationError("背景提取：输入图像为空")

        method = self._normalize_method(str(self.parameters["method"]))
        if method == "Average":
            mask = self._apply_average(mat)
            background = self._average_background
        elif method in {"MOG2", "KNN"}:
            mask = self._apply_cv_subtractor(mat, method)
            background = self._get_cv_background()
        else:
            raise OperationError(f"背景提取：不支持的建模方法 {method!r}")

        return self._format_output(mat, mask, background)

    def _apply_average(self, mat: np.ndarray) -> np.ndarray:
        frame = self._as_bgr(mat)
        if self._average_background is None:
            self._average_background = frame.copy()

        diff = cv2.absdiff(frame, self._average_background)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, int(self.parameters["threshold"]), 255, cv2.THRESH_BINARY)
        return mask

    def _apply_cv_subtractor(self, mat: np.ndarray, method: str) -> np.ndarray:
        subtractor = self._ensure_cv_subtractor(method)
        learning_rate = float(self.parameters["learning_rate"])
        try:
            return subtractor.apply(mat, learningRate=learning_rate)
        except cv2.error as exc:
            raise OperationError(f"背景提取 {method} 执行失败：{exc}") from exc

    def _ensure_cv_subtractor(self, method: str) -> cv2.BackgroundSubtractor:
        signature = (
            method,
            int(self.parameters["history"]),
            int(self.parameters["threshold"]),
            bool(self.parameters["detect_shadows"]),
        )
        if self._subtractor is not None and self._subtractor_signature == signature:
            return self._subtractor

        history = int(self.parameters["history"])
        threshold = int(self.parameters["threshold"])
        detect_shadows = bool(self.parameters["detect_shadows"])
        if method == "MOG2":
            self._subtractor = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=threshold,
                detectShadows=detect_shadows,
            )
        else:
            self._subtractor = cv2.createBackgroundSubtractorKNN(
                history=history,
                dist2Threshold=float(threshold * threshold),
                detectShadows=detect_shadows,
            )
        self._subtractor_signature = signature
        return self._subtractor

    def _get_cv_background(self) -> Optional[np.ndarray]:
        if self._subtractor is None:
            return None
        try:
            return self._subtractor.getBackgroundImage()
        except cv2.error:
            return None

    def _format_output(
        self,
        mat: np.ndarray,
        mask: np.ndarray,
        background: Optional[np.ndarray],
    ) -> np.ndarray:
        output = self._normalize_output(str(self.parameters["output"]))
        if output == "Mask":
            return mask
        if output == "Background":
            if background is None:
                return np.zeros_like(mat)
            return background

        foreground = cv2.bitwise_and(mat, mat, mask=mask)
        return foreground

    @staticmethod
    def _as_bgr(mat: np.ndarray) -> np.ndarray:
        if mat.ndim == 2:
            return cv2.cvtColor(mat, cv2.COLOR_GRAY2BGR)
        if mat.ndim == 3 and mat.shape[2] == 3:
            return mat
        if mat.ndim == 3 and mat.shape[2] == 4:
            return cv2.cvtColor(mat, cv2.COLOR_BGRA2BGR)
        raise OperationError(f"不支持的图像尺寸或通道：{mat.shape}")

    @staticmethod
    def _normalize_method(method: str) -> str:
        if method in {"平均法", "Average", "average", "avg"}:
            return "Average"
        return method

    @staticmethod
    def _normalize_output(output: str) -> str:
        if output in {"前景", "Foreground"}:
            return "Foreground"
        if output in {"掩码", "Mask"}:
            return "Mask"
        if output in {"背景", "Background"}:
            return "Background"
        return output
