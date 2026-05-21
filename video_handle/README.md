# Video Frame Exporter

商业级 PySide6 + FFmpeg 批量视频转图片工具。

## 架构

项目采用 MVC 架构：

```text
models.py      # Model：视频队列、提取配置、QSettings 配置存档
ui_main.py     # View：主窗口界面、表单采集、拖拽和状态展示
controller.py  # Controller：连接 View/Model/Worker，调度后台任务
worker.py      # 后台 Worker：构造并执行 FFmpeg 命令
utils.py       # 通用工具：ffprobe、路径、时间、文件收集
main.py        # 应用入口
```

## 运行

```powershell
pip install -r requirements.txt
python main.py
```

需要系统已安装 FFmpeg，并确保 `ffmpeg` 与 `ffprobe` 在 `PATH` 中。

## 打包

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name VideoFrameExporter --add-data "styles.qss;." main.py
```

打包后仍建议将 FFmpeg 安装到系统 PATH。若需要随包分发 FFmpeg，可把 `ffmpeg.exe` 和 `ffprobe.exe` 放入项目目录，并在打包命令里添加对应 `--add-binary` 参数。

## 文件名模板

兼容 FFmpeg 原生序列写法：

```text
%06d
frame_%04d
```

也支持更直观的变量写法：

```text
{video}_{index:06d}
{date}_{video}_{index}
{datetime}_{video}_{index:04d}
```

可用变量：

- `{video}`：视频文件名，不含扩展名。
- `{date}`：当前日期，例如 `20260515`。
- `{time}`：当前时间，例如 `101530`。
- `{datetime}`：当前日期时间，例如 `20260515_101530`。
- `{index}`：序号，等价于 `%06d`。
- `{index:04d}`、`{index:06d}`、`{index:08d}`：指定序号位数。

## 配置存档

程序会自动保存上次使用的配置，并在下次启动时恢复：

- 窗口大小和位置
- 提取模式
- FPS、间隔秒数、总帧数、起止时间
- 图片格式和质量参数
- 输出文件夹
- 文件名模板

配置使用 Qt `QSettings` 存储，不需要手动维护配置文件。
