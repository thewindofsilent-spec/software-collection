# AutoLabel - 半监督自动标注工具

基于 PySide6 + QML + Python 开发的半监督自动标注工具，支持YOLO模型训练和批量自动标注。

## 功能特性

- **图像管理**：支持导入图像文件夹（含子文件夹），自动区分已标注/未标注图像
- **模型训练**：使用已标注数据转换为YOLO格式，一键启动训练
- **自动标注**：使用YOLO模型批量推理，生成标准LabelMe格式JSON
- **可视化校正**：在图像上叠加绘制矩形框和关键点，支持手动添加/删除/修改
- **大文件夹支持**：虚拟化列表技术，几千张图像不卡顿
- **配置持久化**：所有设置保存到配置文件，支持加载已有配置

## 项目结构

```
auto_label/
├── main.py                 # 主程序入口
├── main.qml                # 主窗口QML
├── requirements.txt        # Python依赖
├── config/
│   ├── settings.py         # 应用配置
│   ├── settings_manager.py # 配置管理器
│   └── settings.json       # 默认配置文件
├── backend/
│   ├── yolo_manager.py     # YOLO模型管理（加载/训练/推理）
│   ├── annotation_manager.py # 标注文件管理
│   ├── dataset_converter.py   # LabelMe→YOLO格式转换
│   └── utils.py           # 工具函数
├── components/             # QML组件（内嵌在main.qml中）
└── models/
    └── annotation.py      # 标注数据模型
```

## 安装依赖

```bash
cd auto_label
pip install -r requirements.txt
```

**依赖列表：**
- PySide6 >= 6.5.0
- ultralytics >= 8.0.0 (YOLOv8/v11)
- opencv-python >= 4.8.0
- numpy >= 1.24.0

## 运行程序

```bash
python main.py
```

程序启动时会自动：
1. 加载 `config/settings.json` 配置文件
2. 自动打开上次加载的图像文件夹

## 使用流程

### 1. 导入图像文件夹

1. 点击菜单 **文件 → 打开文件夹...**
2. 选择包含图像的文件夹
3. 左侧列表显示所有图像，已标注（绿色）未标注（灰色）

### 2. 加载YOLO模型

1. 点击菜单 **文件 → 加载模型...**
2. 选择训练好的 `.pt` 模型文件
3. 状态栏显示"模型已加载"

### 3. 自动标注（批量推理）

1. 点击菜单 **工具 → 自动标注...**
2. 设置参数：
   - **源图像**：待标注图像文件夹（可点击浏览选择）
   - **输出目录**：生成JSON文件的保存位置（可点击浏览选择）
   - **置信度阈值**：默认0.25
   - **IoU阈值**：默认0.45
   - **最大检测数**：默认300
3. 点击确定开始批量推理
4. 进度条显示处理进度
5. 完成后自动更新图像列表状态

### 4. 手动校正标注

1. 在左侧列表点击选择图像
2. 中间显示图像和叠加的标注
3. 右侧显示所有形状列表

**操作：**
- 滚轮缩放图像
- Shift+拖拽平移图像
- 右键菜单添加矩形框或关键点
- 点击形状列表的"删除"按钮删除

### 5. 模型训练

1. 先使用已有数据或手动标注部分图像
2. 点击菜单 **工具 → 转换数据集...**
3. 将LabelMe格式转换为YOLO格式
4. 点击菜单 **工具 → 训练...**
5. 设置参数后开始训练
6. 训练完成后模型保存在 `runs/detect/train/weights/best.pt`

### 6. 保存标注

1. 选择图像后修改标注
2. 点击菜单 **文件 → 保存标注**
3. 生成同名 `.json` 文件

## 配置管理

### 配置文件格式

配置文件为JSON格式，包含以下内容：

```json
{
    "training": {
        "epochs": 100,
        "batch": 16,
        "imgsz": 640,
        "workers": 8,
        "patience": 50,
        "project": "runs/detect",
        "name": "train"
    },
    "auto_label": {
        "conf": 0.25,
        "iou": 0.45,
        "max_det": 300
    },
    "paths": {
        "last_image_dir": "D:/images",
        "last_model_path": "",
        "last_output_dir": "",
        "last_dataset_yaml": ""
    }
}
```

### 配置菜单

- **文件 → 加载配置...**：加载已有的配置文件
- **文件 → 保存配置...**：将当前设置保存为新配置文件

### 自动保存

程序退出时会自动保存当前配置到 `config/settings.json`

### 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| training.epochs | 训练轮数 | 100 |
| training.batch | 批大小 | 16 |
| training.imgsz | 图像尺寸 | 640 |
| training.workers | 工作进程数 | 8 |
| training.patience | 早停耐心值 | 50 |
| auto_label.conf | 置信度阈值 | 0.25 |
| auto_label.iou | IoU阈值 | 0.45 |
| auto_label.max_det | 最大检测数 | 300 |
| paths.last_image_dir | 上次打开的文件夹 | - |
| paths.last_model_path | 上次加载的模型 | - |
| paths.last_output_dir | 上次选择的输出目录 | - |

## LabelMe JSON格式

生成的标准LabelMe格式：

```json
{
  "version": "5.2.0",
  "flags": {},
  "shapes": [
    {
      "label": "mouse",
      "points": [[x1, y1], [x2, y2]],
      "group_id": null,
      "description": "",
      "shape_type": "rectangle",
      "flags": {}
    },
    {
      "label": "0",
      "points": [[x, y]],
      "group_id": null,
      "description": "",
      "shape_type": "point",
      "flags": {}
    }
  ],
  "imagePath": "filename.jpg",
  "imageData": null,
  "imageHeight": 720,
  "imageWidth": 1280
}
```

## 键盘快捷键

| 操作 | 快捷键 |
|------|--------|
| 缩放 | 滚轮 |
| 平移 | Shift + 拖拽 |
| 右键菜单 | 右键点击 |

## 线程安全说明

- **训练和批量推理**在后台线程执行，不阻塞UI
- 通过Qt信号（Signal）更新进度条和状态消息
- Python与QML通过Property/Signal/Slot机制通信

## 注意事项

1. **首次使用**：需要先手动标注部分图像，再用这些数据训练初始模型
2. **大文件夹**：建议先在小文件夹测试，确认功能正常后再处理大文件夹
3. **模型格式**：支持YOLOv8/v11的 `.pt` 格式模型
4. **图像格式**：支持 jpg、jpeg、png、bmp、tiff、webp
5. **保存标注**：修改标注后记得保存，否则关闭程序后丢失
6. **配置文件**：建议定期保存配置，避免丢失设置

## 常见问题

**Q: 图像显示不出来**
A: 检查是否正确加载了模型和选择了图像

**Q: 自动标注没有反应**
A: 确认已加载模型，且源文件夹中有未标注的图像

**Q: 训练失败**
A: 检查dataset.yaml配置是否正确，确保有足够的已标注数据

**Q: 如何保存不同项目的配置？**
A: 使用"文件 → 保存配置..."可以将当前配置保存为新文件，便于不同项目切换

## 技术栈

- **UI**: QML (Qt 6.5+)
- **后端**: Python + PySide6
- **深度学习**: ultralytics (YOLOv8/v11)
- **图像处理**: OpenCV
