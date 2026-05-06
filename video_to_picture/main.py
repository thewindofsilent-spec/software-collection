import os
import sys
import cv2
from PySide6.QtCore import QObject, Signal, QThread, Property, Slot
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType


class ExtractThread(QThread):
    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, video_path, output_dir, interval, start_frame, end_frame, img_format="png"):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.interval = interval
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.img_format = img_format

    def run(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error.emit(f"无法打开视频: {self.video_path}")
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            if self.end_frame > 0:
                total_frames = min(total_frames, self.end_frame)

            frame_count = 0
            saved_count = 0

            cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

            ext = f".{self.img_format.lower()}"
            if self.img_format.lower() == "jpg":
                ext = ".jpg"

            self.log.emit(f"开始提取... | 总帧数: {total_frames} | FPS: {fps:.2f}")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_pos = self.start_frame + frame_count

                if self.end_frame > 0 and current_pos > self.end_frame:
                    break

                if current_pos % self.interval == 0:
                    filename = f"frame_{current_pos:06d}{ext}"
                    filepath = os.path.join(self.output_dir, filename)
                    cv2.imwrite(filepath, frame)
                    saved_count += 1
                    self.log.emit(f"已保存: {filename}")

                frame_count += 1
                self.progress.emit(frame_count, total_frames)

                if self.end_frame > 0 and current_pos >= self.end_frame:
                    break

            cap.release()

            self.finished.emit(f"提取完成! 共保存 {saved_count} 帧")

        except Exception as e:
            self.error.emit(str(e))


class VideoToPicture(QObject):
    extractingChanged = Signal()
    progressCurrentChanged = Signal()
    progressTotalChanged = Signal()
    logTextChanged = Signal()
    videoPathChanged = Signal()
    outputPathChanged = Signal()

    def __init__(self):
        super().__init__()
        self._video_path = ""
        self._output_path = ""
        self._extracting = False
        self._progress_current = 0
        self._progress_total = 0
        self._log_text = ""
        self._extract_thread = None

    @Property(str, notify=videoPathChanged)
    def videoPath(self):
        return self._video_path

    @videoPath.setter
    def videoPath(self, path: str):
        self._video_path = path
        self.videoPathChanged.emit()

    @Property(str, notify=outputPathChanged)
    def outputPath(self):
        return self._output_path

    @outputPath.setter
    def outputPath(self, path: str):
        self._output_path = path
        self.outputPathChanged.emit()

    @Property(bool, notify=extractingChanged)
    def extracting(self):
        return self._extracting

    @Property(int, notify=progressCurrentChanged)
    def progressCurrent(self):
        return self._progress_current

    @Property(int, notify=progressTotalChanged)
    def progressTotal(self):
        return self._progress_total

    @Property(str, notify=logTextChanged)
    def logText(self):
        return self._log_text

    @Property(str, notify=logTextChanged)
    def logText(self):
        return self._log_text

    @Slot(str)
    def selectVideo(self, path: str = ""):
        from PySide6.QtWidgets import QFileDialog
        if not path:
            parent = QApplication.instance()
            path, _ = QFileDialog.getOpenFileName(
                parent, "选择视频文件", "", "视频文件 (*.avi *.mp4 *.mov *.mkv);;所有文件 (*)"
            )
        if path:
            self.videoPath = path
            self._add_log(f"已选择视频: {path}")

    @Slot(str)
    def selectOutput(self, path: str = ""):
        from PySide6.QtWidgets import QFileDialog
        if not path:
            parent = QApplication.instance()
            path = QFileDialog.getExistingDirectory(parent, "选择输出目录")
        if path:
            self.outputPath = path
            self._add_log(f"输出目录: {path}")

    def startExtract(self, interval: int, start_frame: int, end_frame: int, img_format: str):
        if not self._video_path:
            self._add_log("错误: 请先选择视频文件")
            return
        if not self._output_path:
            self._add_log("错误: 请先选择输出目录")
            return

        self._extracting = True
        self.extractingChanged.emit()
        self._progress_current = 0
        self._progress_total = 0
        self.progressCurrentChanged.emit()
        self.progressTotalChanged.emit()
        self._add_log("正在提取...")

        self._extract_thread = ExtractThread(
            self._video_path, self._output_path, interval, start_frame, end_frame, img_format
        )
        self._extract_thread.progress.connect(self._on_progress)
        self._extract_thread.finished.connect(self._on_finished)
        self._extract_thread.error.connect(self._on_error)
        self._extract_thread.log.connect(self._on_log)
        self._extract_thread.start()

    def _on_progress(self, current, total):
        self._progress_current = current
        self._progress_total = total
        self.progressCurrentChanged.emit()
        self.progressTotalChanged.emit()

    def _on_finished(self, msg):
        self._extracting = False
        self.extractingChanged.emit()
        self._add_log(msg)

    def _on_error(self, err):
        self._extracting = False
        self.extractingChanged.emit()
        self._add_log(f"错误: {err}")

    def _on_log(self, msg):
        self._add_log(msg)

    def _add_log(self, msg: str):
        self._log_text += msg + "\n"
        self.logTextChanged.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    qmlRegisterType(VideoToPicture, "VideoToPicture", 1, 0, "VideoToPicture")

    engine = QQmlApplicationEngine()
    engine.load(os.path.join(os.path.dirname(__file__), "main.qml"))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())