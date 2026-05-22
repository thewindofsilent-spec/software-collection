from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QRubberBand,
)


class ViewerMode(Enum):
    """Interaction mode used by ImageViewer."""

    PAN = auto()
    ROI = auto()


@dataclass(frozen=True)
class PixelInfo:
    """Pixel information emitted while the mouse moves over the image."""

    x: int
    y: int
    bgr: Tuple[int, int, int]
    hsv: Tuple[int, int, int]


class ImageViewer(QGraphicsView):
    """Professional OpenCV image viewer based on QGraphicsView.

    Features:
        - Fast pixmap display for OpenCV Mat / numpy.ndarray.
        - Mouse wheel zoom, Ctrl + wheel fine zoom.
        - Hand-drag panning.
        - ROI rubber-band selection, emitted as QRectF in image coordinates.
        - Named overlay layers for masks, contours, heatmaps, etc.
        - Real-time image coordinate and BGR/HSV pixel inspection.
    """

    roiSelected = Signal(QRectF)
    mousePixelChanged = Signal(object)
    mouseLeftImage = Signal()
    zoomChanged = Signal(float)

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._image_item = QGraphicsPixmapItem()
        self._image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._image_item.setZValue(0.0)
        self._scene.addItem(self._image_item)

        self._roi_item = QGraphicsRectItem()
        self._roi_item.setPen(QPen(QColor(72, 160, 255), 1.5, Qt.PenStyle.DashLine))
        self._roi_item.setBrush(QColor(72, 160, 255, 35))
        self._roi_item.setZValue(1000.0)
        self._roi_item.hide()
        self._scene.addItem(self._roi_item)

        self._overlays: Dict[str, QGraphicsPixmapItem] = {}
        self._image_bgr: Optional[np.ndarray] = None
        self._image_hsv: Optional[np.ndarray] = None
        self._image_rect = QRectF()

        self._mode = ViewerMode.PAN
        self._zoom = 1.0
        self._min_zoom = 0.02
        self._max_zoom = 80.0
        self._zoom_step = 1.25
        self._fine_zoom_step = 1.05

        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._roi_origin_view = QPoint()
        self._selecting_roi = False

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.viewport().setMouseTracking(True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setBackgroundBrush(QColor(30, 30, 30))

    @property
    def mode(self) -> ViewerMode:
        return self._mode

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    def set_mode(self, mode: ViewerMode) -> None:
        self._mode = mode
        if mode == ViewerMode.PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def set_image(self, image: np.ndarray, *, color_space: str = "BGR", fit: bool = True) -> None:
        """Display an OpenCV Mat / numpy image.

        Args:
            image: Input image. Supports Gray, BGR, RGB, BGRA, RGBA.
            color_space: Declares input color layout: BGR, RGB, BGRA, RGBA, GRAY.
            fit: Fit image to the viewport after setting it.
        """

        if image is None or image.size == 0:
            raise ValueError("image must be a non-empty numpy array")

        self._image_bgr = self._to_bgr(image, color_space)
        self._image_hsv = cv2.cvtColor(self._image_bgr, cv2.COLOR_BGR2HSV)

        pixmap = self.cv_mat_to_qpixmap(image, color_space=color_space)
        self._image_item.setPixmap(pixmap)
        self._image_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        self._scene.setSceneRect(self._image_rect)
        self._roi_item.hide()

        for overlay in self._overlays.values():
            overlay.setOffset(0, 0)

        if fit:
            self.fit_to_view()

    def clear_image(self) -> None:
        self._image_item.setPixmap(QPixmap())
        self._image_bgr = None
        self._image_hsv = None
        self._image_rect = QRectF()
        self._scene.setSceneRect(QRectF())
        self.clear_overlays()
        self._roi_item.hide()

    def add_overlay(
        self,
        name: str,
        overlay: np.ndarray,
        *,
        color_space: str = "BGRA",
        opacity: float = 0.45,
        z_value: float = 10.0,
    ) -> None:
        """Add or replace a named overlay layer.

        Typical inputs:
            - binary mask: uint8 HxW
            - colored mask: uint8 HxWx3
            - alpha layer: uint8 HxWx4
        """

        if overlay is None or overlay.size == 0:
            raise ValueError("overlay must be a non-empty numpy array")

        pixmap = self.cv_mat_to_qpixmap(overlay, color_space=color_space)
        item = self._overlays.get(name)
        if item is None:
            item = QGraphicsPixmapItem()
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self._scene.addItem(item)
            self._overlays[name] = item

        item.setPixmap(pixmap)
        item.setOpacity(max(0.0, min(1.0, opacity)))
        item.setZValue(z_value)
        item.setVisible(True)

    def add_mask_overlay(
        self,
        name: str,
        mask: np.ndarray,
        *,
        color: Tuple[int, int, int] = (0, 255, 0),
        opacity: float = 0.35,
    ) -> None:
        if mask.ndim != 2:
            raise ValueError("mask overlay expects a single-channel image")

        alpha = np.where(mask > 0, int(255 * opacity), 0).astype(np.uint8)
        b, g, r = color
        colored = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        colored[..., 0] = b
        colored[..., 1] = g
        colored[..., 2] = r
        colored[..., 3] = alpha
        self.add_overlay(name, colored, color_space="BGRA", opacity=1.0)

    def add_contours_overlay(
        self,
        name: str,
        contours: Tuple[np.ndarray, ...] | list[np.ndarray],
        size: Tuple[int, int],
        *,
        color: Tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
    ) -> None:
        width, height = size
        layer = np.zeros((height, width, 4), dtype=np.uint8)
        cv2.drawContours(layer, contours, -1, (*color, 255), thickness)
        self.add_overlay(name, layer, color_space="BGRA", opacity=1.0)

    def set_overlay_visible(self, name: str, visible: bool) -> None:
        if name in self._overlays:
            self._overlays[name].setVisible(visible)

    def remove_overlay(self, name: str) -> None:
        item = self._overlays.pop(name, None)
        if item is not None:
            self._scene.removeItem(item)

    def clear_overlays(self) -> None:
        for item in self._overlays.values():
            self._scene.removeItem(item)
        self._overlays.clear()

    def fit_to_view(self) -> None:
        if self._image_rect.isNull():
            return
        self.fitInView(self._image_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoomChanged.emit(self._zoom)

    def actual_size(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)

    def zoom_in(self, fine: bool = False) -> None:
        self._apply_zoom(self._fine_zoom_step if fine else self._zoom_step)

    def zoom_out(self, fine: bool = False) -> None:
        step = self._fine_zoom_step if fine else self._zoom_step
        self._apply_zoom(1.0 / step)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._image_rect.isNull():
            event.ignore()
            return

        fine = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        step = self._fine_zoom_step if fine else self._zoom_step
        factor = step if event.angleDelta().y() > 0 else 1.0 / step
        self._apply_zoom(factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._mode == ViewerMode.ROI and event.button() == Qt.MouseButton.LeftButton:
            self._selecting_roi = True
            self._roi_origin_view = event.pos()
            self._rubber_band.setGeometry(QRectF(event.pos(), event.pos()).toRect())
            self._rubber_band.show()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting_roi:
            rect = QRectF(self._roi_origin_view, event.pos()).normalized().toRect()
            self._rubber_band.setGeometry(rect)
            event.accept()
        else:
            super().mouseMoveEvent(event)

        self._emit_pixel_info(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._selecting_roi and event.button() == Qt.MouseButton.LeftButton:
            self._selecting_roi = False
            self._rubber_band.hide()

            view_rect = QRectF(self._roi_origin_view, event.pos()).normalized()
            scene_top_left = self.mapToScene(view_rect.topLeft().toPoint())
            scene_bottom_right = self.mapToScene(view_rect.bottomRight().toPoint())
            roi = QRectF(scene_top_left, scene_bottom_right).normalized()
            roi = roi.intersected(self._image_rect)

            if roi.width() >= 1.0 and roi.height() >= 1.0:
                self._roi_item.setRect(roi)
                self._roi_item.show()
                self.roiSelected.emit(roi)

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event: object) -> None:
        self.mouseLeftImage.emit()
        super().leaveEvent(event)

    def _apply_zoom(self, factor: float) -> None:
        new_zoom = self._zoom * factor
        if new_zoom < self._min_zoom:
            factor = self._min_zoom / self._zoom
            new_zoom = self._min_zoom
        elif new_zoom > self._max_zoom:
            factor = self._max_zoom / self._zoom
            new_zoom = self._max_zoom

        self.scale(factor, factor)
        self._zoom = new_zoom
        self.zoomChanged.emit(self._zoom)

    def _emit_pixel_info(self, view_pos: QPoint) -> None:
        if self._image_bgr is None or self._image_hsv is None:
            return

        scene_pos = self.mapToScene(view_pos)
        x = int(scene_pos.x())
        y = int(scene_pos.y())
        height, width = self._image_bgr.shape[:2]
        if x < 0 or y < 0 or x >= width or y >= height:
            self.mouseLeftImage.emit()
            return

        bgr_raw = self._image_bgr[y, x]
        hsv_raw = self._image_hsv[y, x]
        bgr = (int(bgr_raw[0]), int(bgr_raw[1]), int(bgr_raw[2]))
        hsv = (int(hsv_raw[0]), int(hsv_raw[1]), int(hsv_raw[2]))
        self.mousePixelChanged.emit(PixelInfo(x=x, y=y, bgr=bgr, hsv=hsv))

    @staticmethod
    def cv_mat_to_qpixmap(image: np.ndarray, *, color_space: str = "BGR") -> QPixmap:
        qimage = ImageViewer.cv_mat_to_qimage(image, color_space=color_space)
        return QPixmap.fromImage(qimage)

    @staticmethod
    def cv_mat_to_qimage(image: np.ndarray, *, color_space: str = "BGR") -> QImage:
        if image is None or image.size == 0:
            raise ValueError("image must be a non-empty numpy array")

        contiguous = np.ascontiguousarray(image)
        color_space = color_space.upper()

        if contiguous.ndim == 2:
            height, width = contiguous.shape
            if contiguous.dtype != np.uint8:
                contiguous = ImageViewer._normalize_to_uint8(contiguous)
            qimage = QImage(
                contiguous.data,
                width,
                height,
                contiguous.strides[0],
                QImage.Format.Format_Grayscale8,
            )
            return qimage.copy()

        if contiguous.ndim != 3:
            raise ValueError("image must be 2D grayscale or 3D color array")

        if contiguous.dtype != np.uint8:
            contiguous = ImageViewer._normalize_to_uint8(contiguous)

        channels = contiguous.shape[2]
        if channels == 3:
            if color_space == "BGR":
                converted = cv2.cvtColor(contiguous, cv2.COLOR_BGR2RGB)
            elif color_space == "RGB":
                converted = contiguous
            elif color_space == "HSV":
                converted = cv2.cvtColor(contiguous, cv2.COLOR_HSV2RGB)
            else:
                raise ValueError(f"unsupported 3-channel color space: {color_space}")

            height, width = converted.shape[:2]
            qimage = QImage(
                converted.data,
                width,
                height,
                converted.strides[0],
                QImage.Format.Format_RGB888,
            )
            return qimage.copy()

        if channels == 4:
            if color_space == "BGRA":
                converted = cv2.cvtColor(contiguous, cv2.COLOR_BGRA2RGBA)
            elif color_space == "RGBA":
                converted = contiguous
            else:
                raise ValueError(f"unsupported 4-channel color space: {color_space}")

            height, width = converted.shape[:2]
            qimage = QImage(
                converted.data,
                width,
                height,
                converted.strides[0],
                QImage.Format.Format_RGBA8888,
            )
            return qimage.copy()

        raise ValueError(f"unsupported channel count: {channels}")

    @staticmethod
    def _to_bgr(image: np.ndarray, color_space: str) -> np.ndarray:
        color_space = color_space.upper()
        contiguous = np.ascontiguousarray(image)

        if contiguous.dtype != np.uint8:
            contiguous = ImageViewer._normalize_to_uint8(contiguous)

        if contiguous.ndim == 2:
            return cv2.cvtColor(contiguous, cv2.COLOR_GRAY2BGR)

        if contiguous.ndim != 3:
            raise ValueError("image must be 2D grayscale or 3D color array")

        channels = contiguous.shape[2]
        if channels == 3:
            if color_space == "BGR":
                return contiguous.copy()
            if color_space == "RGB":
                return cv2.cvtColor(contiguous, cv2.COLOR_RGB2BGR)
            if color_space == "HSV":
                return cv2.cvtColor(contiguous, cv2.COLOR_HSV2BGR)
        elif channels == 4:
            if color_space == "BGRA":
                return cv2.cvtColor(contiguous, cv2.COLOR_BGRA2BGR)
            if color_space == "RGBA":
                return cv2.cvtColor(contiguous, cv2.COLOR_RGBA2BGR)

        raise ValueError(f"unsupported image format: {color_space}, shape={image.shape}")

    @staticmethod
    def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
        if image.dtype == np.bool_:
            return (image.astype(np.uint8) * 255)

        min_value = float(np.nanmin(image))
        max_value = float(np.nanmax(image))
        if max_value <= min_value:
            return np.zeros(image.shape, dtype=np.uint8)

        normalized = (image.astype(np.float32) - min_value) * (255.0 / (max_value - min_value))
        return np.clip(normalized, 0, 255).astype(np.uint8)
