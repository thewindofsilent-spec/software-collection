import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window

ApplicationWindow {
    id: mainWindow
    width: 1400
    height: 900
    minimumWidth: 1000
    minimumHeight: 700
    title: "AutoLabel - 半监督自动标注工具"

    visible: true
    color: "#1e1e1e"

    // 全局样式定义
    property color primaryColor: "#0078d4"
    property color successColor: "#4ec94e"
    property color warningColor: "#ff9800"
    property color dangerColor: "#f44336"
    property color bgDark: "#1e1e1e"
    property color bgPanel: "#252526"
    property color bgTitle: "#2d2d2d"

    // 菜单栏
    menuBar: MenuBar {
        background: Rectangle { color: bgTitle }
        Menu {
            title: "文件"
            MenuItem { text: "打开文件夹..."; onTriggered: folderDialog.open() }
            MenuItem { text: "加载模型..."; onTriggered: modelDialog.open() }
            MenuItem { text: "保存标注"; onTriggered: saveAnnotation() }
            MenuItem { text: "加载配置..."; onTriggered: loadConfigDialog.open() }
            MenuItem { text: "保存配置..."; onTriggered: saveConfigDialog.open() }
            MenuItem { text: "退出"; onTriggered: Qt.quit() }
        }
        Menu {
            title: "工具"
            MenuItem { text: "转换数据集..."; onTriggered: convertDialog.open() }
            MenuItem { text: "模型训练..."; onTriggered: trainingDialog.open() }
            MenuItem { text: "自动标注..."; onTriggered: autoLabelDialog.open() }
        }
        Menu {
            title: "帮助"
            MenuItem { text: "关于" }
        }
    }

    // 刷新图像列表
    function refreshImageList() {
        imageListModel.clear()
        var count = controller.getImageCount()
        console.log("refreshImageList called, count:", count)
        for (var i = 0; i < count; i++) {
            var img = controller.getImageAt(i)
            console.log("  image", i, ":", JSON.stringify(img))
            if (img) imageListModel.append({index: i, path: img.path, name: img.name, annotated: img.annotated})
        }
    }

    // 主布局
    RowLayout {
        anchors.fill: parent
        anchors.bottomMargin: 28
        spacing: 0

        // ========== 左侧面板 - 图像列表 ==========
        Rectangle {
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            color: bgPanel

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredHeight: 40
                    Layout.fillWidth: true
                    color: bgTitle
                    Text {
                        anchors.centerIn: parent
                        text: "图像列表 (" + imageListModel.count + ")"
                        color: "#cccccc"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: bgDark

                    ListModel { id: imageListModel }

                    ListView {
                        id: imageListView
                        anchors.fill: parent
                        model: imageListModel
                        clip: true
                        currentIndex: -1

                        delegate: Rectangle {
                            width: parent ? parent.width : 0
                            height: 60
                            color: ListView.isCurrentItem ? "#094771" : (model.annotated ? "#2d4a2d" : "transparent")
                            border.width: ListView.isCurrentItem ? 1 : 0
                            border.color: primaryColor

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10
                                padding: 8

                                Rectangle {
                                    width: 50
                                    height: 44
                                    color: "#333333"
                                    radius: 4
                                    Image {
                                        anchors.fill: parent
                                        source: "image://imageProvider/" + model.path
                                        fillMode: Image.PreserveAspectCrop
                                        smooth: true
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4
                                    Text {
                                        text: model.name
                                        color: "#ffffff"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        maximumLineCount: 1
                                    }
                                    Text {
                                        text: model.annotated ? "已标注" : "待标注"
                                        color: model.annotated ? successColor : "#888888"
                                        font.pixelSize: 11
                                    }
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    imageListView.currentIndex = index
                                    controller.selectImage(index)
                                }
                            }
                        }
                        ScrollBar.vertical: ScrollBar { active: true; width: 8 }
                    }
                }
            }
        }

        // ========== 中间面板 - 图像查看器 ==========
        Rectangle {
            id: imageViewer
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: bgDark

            property real scaleFactor: 1.0
            property real minScale: 0.1
            property real maxScale: 10.0
            property point panOffset: Qt.point(0, 0)
            property bool isPanning: false
            property point lastMouse: Qt.point(0, 0)
            property int imageWidth: controller.getImageWidth()
            property int imageHeight: controller.getImageHeight()

            Rectangle {
                id: canvasContainer
                anchors.centerIn: parent
                width: mainWindow.width * imageViewer.scaleFactor
                height: mainWindow.height * imageViewer.scaleFactor
                color: "#1a1a1a"
                transform: Translate {
                    x: imageViewer.panOffset.x
                    y: imageViewer.panOffset.y
                }

                Image {
                    id: displayImage
                    anchors.centerIn: parent
                    source: "image://imageProvider"
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    cache: false

                    Rectangle {
                        id: overlayCanvas
                        anchors.fill: parent
                        color: "transparent"

                        Canvas {
                            id: annotationCanvas
                            anchors.fill: parent
                            contextType: "2d"

                            onPaint: {
                                var ctx = annotationCanvas.getContext("2d")
                                ctx.clearRect(0, 0, annotationCanvas.width, annotationCanvas.height)
                                var scaleX = annotationCanvas.width / (imageViewer.imageWidth || 1)
                                var scaleY = annotationCanvas.height / (imageViewer.imageHeight || 1)

                                var shapes = []
                                for (var i = 0; i < controller.getShapeCount(); i++) {
                                    var shape = controller.getShape(i)
                                    if (shape) shapes.push(shape)
                                }

                                for (var i = 0; i < shapes.length; i++) {
                                    var shape = shapes[i]
                                    if (shape.shapeType === "rectangle") {
                                        var points = shape.points
                                        if (points && points.length >= 2) {
                                            ctx.strokeStyle = "#00ff00"
                                            ctx.lineWidth = 2
                                            ctx.strokeRect(
                                                points[0][0] * scaleX, points[0][1] * scaleY,
                                                (points[1][0] - points[0][0]) * scaleX,
                                                (points[1][1] - points[0][1]) * scaleY
                                            )
                                            ctx.fillStyle = "#00ff00"
                                            ctx.font = "12px sans-serif"
                                            ctx.fillText(shape.label, points[0][0] * scaleX, points[0][1] * scaleY - 5)
                                        }
                                    } else if (shape.shapeType === "point") {
                                        var points = shape.points
                                        if (points && points.length >= 1) {
                                            var x = points[0][0] * scaleX
                                            var y = points[0][1] * scaleY
                                            ctx.fillStyle = "#ff0000"
                                            ctx.beginPath()
                                            ctx.arc(x, y, 6, 0, Math.PI * 2)
                                            ctx.fill()
                                            ctx.fillStyle = "#ffffff"
                                            ctx.beginPath()
                                            ctx.arc(x, y, 3, 0, Math.PI * 2)
                                            ctx.fill()
                                            ctx.fillStyle = "#ffff00"
                                            ctx.font = "bold 10px sans-serif"
                                            ctx.fillText(shape.label, x + 8, y + 4)
                                        }
                                    }
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                            onPressed: {
                                if (mouse.button === Qt.MiddleButton || (mouse.button === Qt.LeftButton && mouse.modifiers & Qt.ShiftModifier)) {
                                    imageViewer.isPanning = true
                                    imageViewer.lastMouse = mouse
                                }
                            }
                            onReleased: { imageViewer.isPanning = false }
                            onPositionChanged: {
                                if (imageViewer.isPanning) {
                                    imageViewer.panOffset.x += mouse.x - imageViewer.lastMouse.x
                                    imageViewer.panOffset.y += mouse.y - imageViewer.lastMouse.y
                                    imageViewer.lastMouse = mouse
                                }
                            }
                            onWheel: {
                                var delta = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                                var newScale = imageViewer.scaleFactor * delta
                                if (newScale >= imageViewer.minScale && newScale <= imageViewer.maxScale) {
                                    var oldScale = imageViewer.scaleFactor
                                    imageViewer.scaleFactor = newScale
                                    var mouseX = wheel.x
                                    var mouseY = wheel.y
                                    imageViewer.panOffset.x = mouseX - (mouseX - imageViewer.panOffset.x) * (newScale / oldScale)
                                    imageViewer.panOffset.y = mouseY - (mouseY - imageViewer.panOffset.y) * (newScale / oldScale)
                                }
                            }
                            onClicked: {
                                if (mouse.button === Qt.RightButton) contextMenu.popup()
                            }
                        }
                    }
                }
            }

            Menu {
                id: contextMenu
                MenuItem {
                    text: "添加矩形框"
                    onTriggered: {
                        var scaleX = annotationCanvas.width / (imageViewer.imageWidth || 1)
                        var scaleY = annotationCanvas.height / (imageViewer.imageHeight || 1)
                        var relX = annotationCanvas.width / 2 / scaleX
                        var relY = annotationCanvas.height / 2 / scaleY
                        controller.addRectangle(controller.imageListModel.selectedIndex, "object",
                            Math.max(0, relX - 50), Math.max(0, relY - 50),
                            Math.min(imageViewer.imageWidth, relX + 50), Math.min(imageViewer.imageHeight, relY + 50))
                        annotationCanvas.requestPaint()
                    }
                }
                MenuItem {
                    text: "添加关键点"
                    onTriggered: {
                        var scaleX = annotationCanvas.width / (imageViewer.imageWidth || 1)
                        var scaleY = annotationCanvas.height / (imageViewer.imageHeight || 1)
                        var relX = annotationCanvas.width / 2 / scaleX
                        var relY = annotationCanvas.height / 2 / scaleY
                        var label = "0"
                        for (var i = 0; i < controller.getShapeCount(); i++) {
                            var shape = controller.getShape(i)
                            if (shape && shape.shapeType === "point") label = String(parseInt(label) + 1)
                        }
                        controller.addPoint(controller.imageListModel.selectedIndex, label, relX, relY)
                        annotationCanvas.requestPaint()
                    }
                }
            }

            Connections {
                target: controller
                function onAnnotationChanged() { annotationCanvas.requestPaint() }
                function onImageListChanged() { refreshImageList() }
            }
        }

        // ========== 右侧面板 - 标注形状列表 ==========
        Rectangle {
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            color: bgPanel

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredHeight: 40
                    Layout.fillWidth: true
                    color: bgTitle
                    Text {
                        anchors.centerIn: parent
                        text: "标注形状 (" + controller.getShapeCount() + ")"
                        color: "#cccccc"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: bgDark

                    ListModel { id: shapeListModel }

                    ListView {
                        id: shapesListView
                        anchors.fill: parent
                        model: shapeListModel
                        clip: true
                        currentIndex: -1

                        delegate: Rectangle {
                            width: parent ? parent.width : 0
                            height: 70
                            color: ListView.isCurrentItem ? "#094771" : bgPanel
                            border.width: ListView.isCurrentItem ? 1 : 0
                            border.color: primaryColor

                            Column {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                Row {
                                    spacing: 8
                                    Rectangle {
                                        width: 20
                                        height: 20
                                        radius: 3
                                        color: model.shapeType === "rectangle" ? successColor : dangerColor
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: model.label || "未命名"
                                        color: "#ffffff"
                                        font.pixelSize: 13
                                        font.bold: true
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: model.shapeType === "rectangle" ? "[矩形]" : "[点]"
                                        color: "#888888"
                                        font.pixelSize: 11
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                Text {
                                    text: {
                                        if (model.shapeType === "rectangle") {
                                            var pts = model.points
                                            if (pts && pts.length >= 2)
                                                return "从 (" + pts[0][0].toFixed(0) + "," + pts[0][1].toFixed(0) +
                                                       ") 到 (" + pts[1][0].toFixed(0) + "," + pts[1][1].toFixed(0) + ")"
                                        } else {
                                            var pts = model.points
                                            if (pts && pts.length >= 1)
                                                return "位于 (" + pts[0][0].toFixed(0) + "," + pts[0][1].toFixed(0) + ")"
                                        }
                                        return ""
                                    }
                                    color: "#aaaaaa"
                                    font.pixelSize: 10
                                }

                                Row {
                                    spacing: 5
                                    Button {
                                        text: "删除"
                                        width: 60
                                        height: 22
                                        font.pixelSize: 10
                                        onClicked: {
                                            controller.removeShape(controller.imageListModel.selectedIndex, index)
                                            refreshShapeList()
                                        }
                                    }
                                }
                            }
                        }
                        ScrollBar.vertical: ScrollBar { active: true; width: 10 }
                    }

                    function refreshShapeList() {
                        shapeListModel.clear()
                        var count = controller.getShapeCount()
                        for (var i = 0; i < count; i++) {
                            var shape = controller.getShape(i)
                            if (shape) shapeListModel.append({index: i, label: shape.label, shapeType: shape.shapeType, points: shape.points})
                        }
                    }

                    Connections {
                        target: controller
                        function onAnnotationChanged() { refreshShapeList() }
                    }
                }
            }
        }
    }

    // ========== 底部状态栏 ==========
    Rectangle {
        id: statusBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        Layout.fillWidth: true
        Layout.preferredHeight: 28
        color: primaryColor

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 10
            text: controller.statusMessage
            color: "#ffffff"
            font.pixelSize: 12
        }

        ProgressBar {
            id: trainProgressBar
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 10
            width: 200
            height: 16
            visible: controller.isTraining
            value: controller.trainProgress
        }

        ProgressBar {
            id: autoLabelProgressBar
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 10
            width: 200
            height: 16
            visible: controller.isAutoLabeling
            value: controller.autoLabelProgress
        }
    }

    // ========== 对话框 ==========
    FolderDialog { id: folderDialog; title: "选择图像文件夹"; onAccepted: controller.loadFolder(folderDialog.currentFolder) }
    FileDialog { id: modelDialog; title: "选择YOLO模型"; nameFilters: ["YOLO模型 (*.pt)", "所有文件 (*)"]; onAccepted: controller.loadModel(modelDialog.currentFile) }
    FileDialog { id: loadConfigDialog; title: "加载配置文件"; nameFilters: ["JSON配置文件 (*.json)", "所有文件 (*)"]; onAccepted: { controller.loadConfig(loadConfigDialog.currentFile); loadConfigValues() } }
    FileDialog { id: saveConfigDialog; title: "保存配置文件"; defaultSuffix: "json"; nameFilters: ["JSON配置文件 (*.json)", "所有文件 (*)"]; onAccepted: controller.saveConfig(saveConfigDialog.currentFile) }
    FileDialog { id: dataYamlDialog; title: "选择数据集YAML"; nameFilters: ["YAML文件 (*.yaml *.yml)", "所有文件 (*)"]; onAccepted: { trainingDialog.dataYaml = dataYamlDialog.currentFile; dataYamlField.text = dataYamlDialog.currentFile } }

    // ========== 数据集转换对话框 ==========
    Dialog {
        id: convertDialog
        title: "转换数据集"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        property string sourceDir: ""
        property string outputDir: ""

        ColumnLayout {
            spacing: 15
            anchors.margins: 20

            Label {
                text: "将LabelMe标注转换为YOLO格式"
                color: "#ffffff"
                font.pixelSize: 14
                font.bold: true
            }

            Row {
                spacing: 10
                Label { text: "源目录:"; color: "#cccccc"; Layout.preferredWidth: 70; verticalAlignment: Text.AlignVCenter }
                TextField {
                    id: convertSourceField
                    text: convertDialog.sourceDir
                    Layout.fillWidth: true
                    placeholderText: "选择包含图像的目录"
                    readOnly: true
                }
                Button {
                    text: "选择"
                    onClicked: convertSourceFolderDialog.open()
                }
            }

            Row {
                spacing: 10
                Label { text: "输出目录:"; color: "#cccccc"; Layout.preferredWidth: 70; verticalAlignment: Text.AlignVCenter }
                TextField {
                    id: convertOutputField
                    text: convertDialog.outputDir
                    Layout.fillWidth: true
                    placeholderText: "选择输出目录"
                }
                Button {
                    text: "选择"
                    onClicked: convertOutputFolderDialog.open()
                }
            }

            CheckBox {
                id: copyImagesCheckbox
                text: "复制图像到输出目录"
                checked: true
            }
        }

        FolderDialog { id: convertSourceFolderDialog; title: "选择源目录"; onAccepted: { convertDialog.sourceDir = convertSourceFolderDialog.currentFolder; convertSourceField.text = convertDialog.sourceDir } }
        FolderDialog { id: convertOutputFolderDialog; title: "选择输出目录"; onAccepted: { convertDialog.outputDir = convertOutputFolderDialog.currentFolder; convertOutputField.text = convertDialog.outputDir } }

        onAccepted: {
            if (!convertDialog.sourceDir || !convertDialog.outputDir) return
            controller.convertDataset(convertDialog.sourceDir, convertDialog.outputDir, copyImagesCheckbox.checked)
        }
    }

    // ========== 训练配置对话框 ==========
    Dialog {
        id: trainingDialog
        title: "训练YOLO模型"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        width: 480
        height: 480

        property int epochs: controller.getConfigValue("training.epochs") || 100
        property int batch: controller.getConfigValue("training.batch") || 16
        property int imgsz: controller.getConfigValue("training.imgsz") || 640
        property int workers: controller.getConfigValue("training.workers") || 8
        property int patience: controller.getConfigValue("training.patience") || 50
        property string dataYaml: ""

        ColumnLayout {
            spacing: 12
            anchors.margins: 20

            Label {
                text: "YOLO训练配置"
                color: "#ffffff"
                font.pixelSize: 16
                font.bold: true
            }

            GridLayout {
                columns: 2
                columnSpacing: 15
                rowSpacing: 10

                Label { text: "数据集YAML:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                Row {
                    spacing: 5
                    Layout.fillWidth: true
                    TextField {
                        id: dataYamlField
                        placeholderText: "path/to/dataset.yaml"
                        Layout.fillWidth: true
                        text: trainingDialog.dataYaml
                        onTextChanged: trainingDialog.dataYaml = text
                    }
                    Button {
                        text: "浏览"
                        onClicked: dataYamlDialog.open()
                    }
                }

                Label { text: "训练轮数:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: epochsSpin
                    from: 1; to: 1000; value: trainingDialog.epochs; stepSize: 10; Layout.fillWidth: true
                    onValueChanged: trainingDialog.epochs = value
                }

                Label { text: "批大小:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: batchSpin
                    from: 1; to: 128; value: trainingDialog.batch; stepSize: 4; Layout.fillWidth: true
                    onValueChanged: trainingDialog.batch = value
                }

                Label { text: "图像尺寸:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: imgszSpin
                    from: 320; to: 1280; value: trainingDialog.imgsz; stepSize: 32; Layout.fillWidth: true
                    onValueChanged: trainingDialog.imgsz = value
                }

                Label { text: "工作进程:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: workersSpin
                    from: 1; to: 32; value: trainingDialog.workers; Layout.fillWidth: true
                    onValueChanged: trainingDialog.workers = value
                }

                Label { text: "早停耐心值:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: patienceSpin
                    from: 5; to: 200; value: trainingDialog.patience; stepSize: 5; Layout.fillWidth: true
                    onValueChanged: trainingDialog.patience = value
                }
            }

            Row {
                spacing: 10
                Layout.alignment: Qt.AlignRight
                ProgressBar {
                    id: trainingProgress
                    width: 200; height: 20
                    visible: controller.isTraining
                    value: controller.trainProgress
                }
                Text {
                    text: controller.isTraining ? "训练中..." : "就绪"
                    color: controller.isTraining ? successColor : "#888888"
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        onAccepted: {
            if (!controller.modelLoaded) {
                controller.setStatusMessage("请先加载YOLO模型")
                return
            }
            var yamlPath = trainingDialog.dataYaml || dataYamlField.text
            if (!yamlPath) {
                controller.setStatusMessage("请选择数据集YAML文件")
                return
            }
            controller.startTraining(
                yamlPath,
                epochsSpin.value, batchSpin.value, imgszSpin.value,
                workersSpin.value, patienceSpin.value, "runs/detect", "train"
            )
        }
    }

    // ========== 自动标注对话框 ==========
    Dialog {
        id: autoLabelDialog
        title: "YOLO自动标注"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        width: 480
        height: 420

        property string sourceDir: controller.getConfigValue("paths.last_image_dir") || ""
        property string outputDir: controller.getConfigValue("paths.last_output_dir") || ""
        property real conf: controller.getConfigValue("auto_label.conf") || 0.25
        property real iou: controller.getConfigValue("auto_label.iou") || 0.45
        property int maxDet: controller.getConfigValue("auto_label.max_det") || 300

        ColumnLayout {
            spacing: 12
            anchors.margins: 20

            Label {
                text: "自动标注配置"
                color: "#ffffff"
                font.pixelSize: 16
                font.bold: true
            }

            Row {
                spacing: 10
                Label { text: "源图像:"; color: "#cccccc"; Layout.preferredWidth: 70; verticalAlignment: Text.AlignVCenter }
                TextField {
                    id: sourceField
                    placeholderText: "选择图像文件夹"
                    text: autoLabelDialog.sourceDir
                    Layout.fillWidth: true
                }
                Button {
                    text: "浏览"
                    onClicked: sourceFolderDialog.open()
                }
            }

            Row {
                spacing: 10
                Label { text: "输出目录:"; color: "#cccccc"; Layout.preferredWidth: 70; verticalAlignment: Text.AlignVCenter }
                TextField {
                    id: outputField
                    placeholderText: "选择输出文件夹"
                    text: autoLabelDialog.outputDir
                    Layout.fillWidth: true
                }
                Button {
                    text: "浏览"
                    onClicked: outputFolderDialog.open()
                }
            }

            GridLayout {
                columns: 2
                columnSpacing: 15
                rowSpacing: 10

                Label { text: "置信度阈值:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                Row {
                    spacing: 5
                    Layout.fillWidth: true
                    Slider {
                        id: confSlider
                        from: 0.01; to: 1.0; value: autoLabelDialog.conf; stepSize: 0.01; Layout.fillWidth: true
                        onValueChanged: autoLabelDialog.conf = value
                    }
                    Text { text: confSlider.value.toFixed(2); color: "#ffffff"; Layout.preferredWidth: 50 }
                }

                Label { text: "IoU阈值:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                Row {
                    spacing: 5
                    Layout.fillWidth: true
                    Slider {
                        id: iouSlider
                        from: 0.01; to: 1.0; value: autoLabelDialog.iou; stepSize: 0.01; Layout.fillWidth: true
                        onValueChanged: autoLabelDialog.iou = value
                    }
                    Text { text: iouSlider.value.toFixed(2); color: "#ffffff"; Layout.preferredWidth: 50 }
                }

                Label { text: "最大检测数:"; color: "#cccccc"; Layout.alignment: Qt.AlignRight }
                SpinBox {
                    id: maxDetSpin
                    from: 1; to: 1000; value: autoLabelDialog.maxDet; Layout.fillWidth: true
                    onValueChanged: autoLabelDialog.maxDet = value
                }
            }

            Row {
                spacing: 10
                Layout.alignment: Qt.AlignRight
                ProgressBar {
                    width: 200; height: 20
                    visible: controller.isAutoLabeling
                    value: controller.autoLabelProgress
                }
                Text {
                    text: controller.isAutoLabeling ? "处理中..." : "就绪"
                    color: controller.isAutoLabeling ? warningColor : "#888888"
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        FolderDialog {
            id: sourceFolderDialog
            title: "选择源图像文件夹"
            onAccepted: {
                autoLabelDialog.sourceDir = sourceFolderDialog.currentFolder
                sourceField.text = autoLabelDialog.sourceDir
            }
        }

        FolderDialog {
            id: outputFolderDialog
            title: "选择输出文件夹"
            onAccepted: {
                autoLabelDialog.outputDir = outputFolderDialog.currentFolder
                outputField.text = autoLabelDialog.outputDir
            }
        }

        onAccepted: {
            if (!controller.modelLoaded) return
            if (!autoLabelDialog.sourceDir) return
            controller.startAutoLabel(
                autoLabelDialog.sourceDir,
                autoLabelDialog.outputDir || autoLabelDialog.sourceDir + "/auto_labeled",
                confSlider.value, iouSlider.value, maxDetSpin.value
            )
        }
    }

    function saveAnnotation() {
        if (imageListView.currentIndex >= 0) {
            var item = imageListModel.get(imageListView.currentIndex)
            if (item) controller.saveCurrentAnnotation(item.path)
        }
    }

    function loadConfigValues() {
        trainingDialog.epochs = controller.getConfigValue("training.epochs") || 100
        trainingDialog.batch = controller.getConfigValue("training.batch") || 16
        trainingDialog.imgsz = controller.getConfigValue("training.imgsz") || 640
        trainingDialog.workers = controller.getConfigValue("training.workers") || 8
        trainingDialog.patience = controller.getConfigValue("training.patience") || 50
        autoLabelDialog.conf = controller.getConfigValue("auto_label.conf") || 0.25
        autoLabelDialog.iou = controller.getConfigValue("auto_label.iou") || 0.45
        autoLabelDialog.maxDet = controller.getConfigValue("auto_label.max_det") || 300
    }

    Component.onCompleted: {
        console.log("AutoLabel主窗口已加载")
        var lastDir = controller.getConfigValue("paths.last_image_dir")
        console.log("Last directory from config:", lastDir)
        if (lastDir && lastDir !== "") {
            console.log("Loading folder:", lastDir)
            controller.loadFolder(lastDir)
            console.log("After loadFolder, imageListModel.count:", imageListModel.count)
        }
    }
}
