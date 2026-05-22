from __future__ import annotations

from typing import ClassVar, Dict

import cv2
import numpy as np

from processing.operation import Operation, OperationError, ParameterDict


_KERNEL_SHAPES: Dict[str, int] = {
    "Rect": cv2.MORPH_RECT,
    "Ellipse": cv2.MORPH_ELLIPSE,
    "Cross": cv2.MORPH_CROSS,
    "矩形": cv2.MORPH_RECT,
    "椭圆": cv2.MORPH_ELLIPSE,
    "十字": cv2.MORPH_CROSS,
}


class MorphologyOperation(Operation):
    """Shared implementation for erosion and dilation."""

    default_parameters: ClassVar[ParameterDict] = {
        "kernel_size": 3,
        "iterations": 1,
        "kernel_shape": "矩形",
    }
    parameter_specs: ClassVar[dict] = {
        "kernel_size": {"type": "int", "label": "核大小", "min": 1, "max": 99, "step": 2},
        "iterations": {"type": "int", "label": "迭代次数", "min": 1, "max": 100},
        "kernel_shape": {
            "type": "choice",
            "label": "核形状",
            "options": ["矩形", "椭圆", "十字"],
        },
    }

    cv_operation: ClassVar[int]

    def apply(self, mat: np.ndarray) -> np.ndarray:
        if mat is None or mat.size == 0:
            raise OperationError(f"{self.name}：输入图像为空")

        kernel_size = max(1, int(self.parameters["kernel_size"]))
        iterations = max(1, int(self.parameters["iterations"]))
        kernel_shape = str(self.parameters["kernel_shape"])

        shape = _KERNEL_SHAPES.get(kernel_shape)
        if shape is None:
            raise OperationError(f"{self.name}：不支持的核形状 {kernel_shape!r}")

        kernel = cv2.getStructuringElement(shape, (kernel_size, kernel_size))
        try:
            return cv2.morphologyEx(mat, self.cv_operation, kernel, iterations=iterations)
        except cv2.error as exc:
            raise OperationError(f"{self.name}执行失败：{exc}") from exc


class Erode(MorphologyOperation):
    operation_type: ClassVar[str] = "Erode"
    name: ClassVar[str] = "腐蚀"
    cv_operation: ClassVar[int] = cv2.MORPH_ERODE


class Dilate(MorphologyOperation):
    operation_type: ClassVar[str] = "Dilate"
    name: ClassVar[str] = "膨胀"
    cv_operation: ClassVar[int] = cv2.MORPH_DILATE
