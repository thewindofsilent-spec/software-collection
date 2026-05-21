# AGENTS.md

## 项目概览

这是一个基于 PySide6 + FFmpeg 的桌面端批量视频转图片工具。

核心能力：

- 拖拽或选择视频文件，支持批量处理。
- 通过 `ffprobe` 读取视频时长、分辨率、帧率和编码信息。
- 通过 `ffmpeg` 提取序列帧，支持 `jpg`、`png`、`webp`。
- 使用 `QThread + QObject Worker` 在后台执行 FFmpeg，避免阻塞 UI。
- 实时解析 FFmpeg `stderr` 中的 `time=HH:MM:SS.xx` 更新进度条。
- 使用 `QSettings` 自动保存并恢复上次配置。
- 默认深色 QSS 主题。

## 文件结构

```text
main.py           # 应用入口，创建 QApplication 和 MainWindow
models.py         # Model：视频队列、提取配置、QSettings 配置存档
ui_main.py        # View：主窗口、拖拽、参数表单、日志、进度条
controller.py     # Controller：连接 View/Model/Worker，调度后台任务
worker.py         # 后台 Worker，负责构造并执行 FFmpeg 命令
utils.py          # FFmpeg 检测、ffprobe 解析、路径/时间工具函数
styles.qss        # 深色主题样式
requirements.txt  # Python 依赖
README.md         # 面向用户的运行和打包说明
AGENTS.md         # 面向开发代理/维护者的工程说明
```

## 运行环境

Python 依赖：

```powershell
pip install -r requirements.txt
```

系统依赖：

- `ffmpeg`
- `ffprobe`

二者应已加入系统环境变量 `PATH`。程序启动时会调用 `utils.ensure_ffmpeg()` 检测。

启动：

```powershell
python main.py
```

## 打包命令

Windows PyInstaller：

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name VideoFrameExporter --add-data "styles.qss;." main.py
```

当前版本默认使用系统 `PATH` 中的 FFmpeg。若需要随包分发 `ffmpeg.exe` 和 `ffprobe.exe`，应在打包命令中增加 `--add-binary`，并同步调整 `utils.find_executable()` 的查找逻辑。

## MVC 架构约定

### Model 层

`models.py` 负责：

- 定义提取模式常量，避免 UI 和 Worker 中散落字符串。
- 定义 `AppConfig`，用于界面配置和配置存档。
- 定义 `ExtractSettings`，用于传递给后台 Worker。
- 定义 `VideoQueueModel`，保存视频队列。
- 定义 `SettingsRepository`，封装 Qt `QSettings`。

Model 不直接操作界面，也不启动 FFmpeg。

### View 层

`ui_main.py` 中的 `MainWindow` 负责：

- 创建 `QMainWindow`、Toolbar、左右分栏、底部日志和进度区。
- 处理拖拽、文件选择等用户输入，并转发给 Controller。
- 根据提取模式动态显示有效参数。
- 从表单采集 `AppConfig`，并展示 Controller 发来的状态。
- 关闭窗口时请求 Controller 保存配置和窗口几何信息。

View 不直接持有视频队列，不直接创建 Worker，也不直接启动 FFmpeg。

### Controller 层

`controller.py` 中的 `MainController` 负责：

- 接收 View 的用户意图。
- 操作 `VideoQueueModel`。
- 调用 `SettingsRepository` 读写配置。
- 读取视频预览信息并通知 View 展示。
- 创建 `QThread`，把 `FrameExtractWorker` 移动到后台线程。
- 接收 Worker 信号并转发给 View。

Controller 不创建具体控件，也不直接修改 UI 控件。

### 配置存档

配置存档位于 Qt `QSettings("CommercialTools", "VideoFrameExporter")`，由系统决定实际落盘位置。

当前保存内容：

- `window/geometry`
- `extract/mode`
- `extract/fps`
- `extract/interval_seconds`
- `extract/total_frames`
- `extract/start_time`
- `extract/end_time`
- `output/format`
- `output/quality`
- `output/directory`
- `output/template`

如果新增 UI 参数，需要同步更新：

- `models.AppConfig`
- `models.SettingsRepository.load_config()`
- `models.SettingsRepository.save_config()`
- `ui_main.MainWindow.collect_config()`
- `ui_main.MainWindow.apply_config()`

### Worker 层

`worker.py` 中的 `FrameExtractWorker` 负责：

- 接收视频列表和 `ExtractSettings`。
- 为每个视频创建独立输出子目录。
- 构造 FFmpeg 参数列表。
- 使用 `subprocess.Popen()` 执行 FFmpeg。
- 逐行读取 `stderr`，解析进度并发出 Qt 信号。
- 响应取消请求，终止当前 FFmpeg 子进程。

FFmpeg 命令必须使用 `list[str]` 参数形式，不要拼接 shell 字符串。这样可以正确处理包含空格、中文和特殊字符的路径。

### Utils 层

`utils.py` 保持无 UI 依赖，适合放置：

- FFmpeg/FFprobe 检测。
- 视频元信息读取。
- 时间格式转换。
- 输出路径和文件名清理。
- 视频文件收集。

## 提取模式

当前支持以下模式：

- `每秒提取 N 帧`
  - UI 显示：`每秒帧数 N`
  - FFmpeg 滤镜：`fps=N`

- `每隔 N 秒提取 1 帧`
  - UI 显示：`间隔秒数 N`
  - FFmpeg 滤镜：`fps=1/N`

- `提取总共 M 帧`
  - UI 显示：`总帧数 M`
  - FFmpeg 滤镜：按视频有效时长估算 fps，并使用 `-frames:v M` 做硬限制。

- `指定起止时间`
  - UI 显示：`起始时间`、`结束时间`、`每秒帧数 N`
  - FFmpeg 参数：`-ss`、`-to`、`fps=N`

如果新增提取模式，需要同步修改：

1. `ui_main.py` 中 `mode_combo` 的选项。
2. `ui_main.py` 中 `update_mode_fields()` 的显隐配置。
3. `worker.py` 中 `_video_filter()` 和必要的命令参数构造逻辑。
4. 如涉及新参数，更新 `ExtractSettings`。

## 输出文件命名

输出目录规则：

- 用户选择一个根输出目录。
- 每个视频会在该目录下创建一个以视频文件名命名的子目录。
- 如果子目录已存在，会自动追加 `_2`、`_3` 等后缀避免覆盖。

文件名模板规则：

- 默认模板为 `%06d`。
- 如果用户输入 `frame_%06d`，输出如 `frame_000001.jpg`。
- 支持变量 `{video}`、`{date}`、`{time}`、`{datetime}`、`{index}`。
- 支持指定序号位数，例如 `{index:04d}`、`{index:06d}`、`{index:08d}`。
- `{index}` 等价于 `%06d`。
- 如果用户输入不含 `%` 的名称，例如 `frame`，会自动转为 `frame_%06d.ext`。
- 如果用户输入带扩展名，例如 `frame.jpg`，会使用当前 UI 选择的格式重写扩展名。

示例：

```text
{video}_{index:06d}
{date}_{video}_{index}
{datetime}_{video}_{index:04d}
```

## 质量参数

UI 中 `质量参数` 范围是 `1-31`：

- `jpg`：直接映射为 `-q:v`，数值越小质量越高。
- `png`：映射为 `-compression_level 0-9`。
- `webp`：映射为 WebP 的 `-q:v 0-100`，保持 UI 上较小数值代表更高质量。

如需更专业的格式独立参数，建议拆成不同格式下的动态字段，而不是复用单个 SpinBox。

## 进度解析

进度来自 FFmpeg `stderr`：

```text
time=00:00:12.34
```

`utils.parse_ffmpeg_time()` 会把该时间转换为秒数。Worker 根据当前文件的有效处理时长计算百分比。

注意：

- 对于 VFR、极短视频、复杂滤镜，FFmpeg 的 `time=` 进度可能不完全线性。
- 当前实现以稳定、通用为优先，不依赖 `-progress pipe:2`。

## 开发注意事项

- 使用 `pathlib.Path` 处理路径。
- 保持中文注释清晰，但不要堆砌无意义注释。
- UI 改动后优先检查控件是否会在深色主题下可读。
- 后台任务只能通过 Qt 信号更新 UI。
- 不要从 Worker 直接访问或修改 UI 控件。
- 不要在 FFmpeg 命令中使用 shell 拼接。
- 不要删除或覆盖用户已有输出，除非用户明确要求。

## 快速验证

语法检查：

```powershell
python -m py_compile main.py ui_main.py worker.py utils.py
```

手动功能检查：

1. 启动 `python main.py`。
2. 拖入一个短视频。
3. 切换四种提取模式，确认只显示有效参数。
4. 选择输出目录。
5. 点击开始，观察日志、当前文件进度和总进度。
6. 点击取消，确认 FFmpeg 子进程停止且 UI 恢复可操作。
