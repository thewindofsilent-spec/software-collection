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
    title: "AutoLabel - Semi-supervised Annotation Tool"

    visible: true

    color: "#1e1e1e"

    menuBar: MenuBar {
        background: Rectangle { color: "#2d2d2d" }

        Menu {
            title: "File"
            MenuItem { text: "Open Folder..."; onTriggered: folderDialog.open() }
            MenuItem { text: "Load Model..."; onTriggered: modelDialog.open() }
            MenuItem { text: "Save"; onTriggered: saveAnnotation() }
            MenuItem { text: "Exit"; onTriggered: Qt.quit() }
        }

        Menu {
            title: "Tools"
            MenuItem { text: "Convert Dataset..."; onTriggered: convertDialog.open() }
            MenuItem { text: "Training..."; onTriggered: trainingDialog.open() }
            MenuItem { text: "Auto Label..."; onTriggered: autoLabelDialog.open() }
        }

        Menu {
            title: "Help"
            MenuItem { text: "About" }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.bottomMargin: 28
        spacing: 0

        Rectangle {
            id: leftPanel
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            color: "#252526"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredHeight: 40
                    Layout.fillWidth: true
                    color: "#2d2d2d"

                    Text {
                        anchors.centerIn: parent
                        text: "Images (" + controller.imageListModel.count + ")"
                        color: "#cccccc"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#1e1e1e"

                    ListView {
                        id: imageListView
                        anchors.fill: parent
                        model: controller.imageListModel
                        clip: true
                        currentIndex: controller.imageListModel.selectedIndex

                        delegate: Rectangle {
                            width: parent ? parent.width : 0
                            height: 60
                            color: ListView.isCurrentItem ? "#094771" : (modelData.annotated ? "#2d4a2d" : "transparent")
                            border.width: ListView.isCurrentItem ? 1 : 0
                            border.color: "#0078d4"

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
                                        source: "image://imageProvider/" + modelData.path
                                        fillMode: Image.PreserveAspectCrop
                                        smooth: true
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4

                                    Text {
                                        text: modelData.name
                                        color: "#ffffff"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        maximumLineCount: 1
                                    }

                                    Text {
                                        text: modelData.annotated ? "Annotated" : "Pending"
                                        color: modelData.annotated ? "#4ec94e" : "#888888"
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

                        ScrollBar.vertical: ScrollBar {
                            active: true
                            width: 8
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e"

            ImageViewer {
                id: imageViewer
                anchors.fill: parent
                anchors.margins: 10
            }
        }

        Rectangle {
            id: rightPanel
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            color: "#252526"

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.preferredHeight: 40
                    Layout.fillWidth: true
                    color: "#2d2d2d"

                    Text {
                        anchors.centerIn: parent
                        text: "Shapes"
                        color: "#cccccc"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#1e1e1e"

                    ShapeList {
                        id: shapeList
                        anchors.fill: parent
                    }
                }
            }
        }
    }

    Rectangle {
        id: statusBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        Layout.fillWidth: true
        Layout.preferredHeight: 28
        color: "#007acc"

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

    FolderDialog {
        id: folderDialog
        title: "Select Image Folder"
        onAccepted: controller.loadFolder(folderDialog.currentFolder)
    }

    FileDialog {
        id: modelDialog
        title: "Select YOLO Model"
        nameFilters: ["YOLO Models (*.pt)", "All Files (*)"]
        onAccepted: controller.loadModel(modelDialog.currentFile)
    }

    FileDialog {
        id: convertDialog
        title: "Select Output Directory"
        fileMode: FolderDialog
        onAccepted: datasetConverterDialog.open()
    }

    Dialog {
        id: datasetConverterDialog
        title: "Convert Dataset"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true

        ColumnLayout {
            spacing: 10

            Label { text: "Converting LabelMe annotations to YOLO format" }
            Label { text: "Source: " + folderDialog.currentFolder }
            Label { text: "Output: " + datasetConverterDialog.currentFolder }

            Row {
                spacing: 10

                CheckBox {
                    id: copyImagesCheckbox
                    text: "Copy images to output"
                    checked: true
                }
            }
        }

        onAccepted: {
            var outputDir = folderDialog.currentFolder + "/yolo_dataset"
            controller.convertDataset(folderDialog.currentFolder, outputDir, copyImagesCheckbox.checked)
        }
    }

    TrainingDialog {
        id: trainingDialog
    }

    AutoLabelDialog {
        id: autoLabelDialog
    }

    function saveAnnotation() {
        if (controller.imageListModel.selectedIndex >= 0) {
            var item = controller.imageListModel.at(controller.imageListModel.selectedIndex)
            if (item) {
                controller.saveCurrentAnnotation(item.path)
            }
        }
    }

    Component.onCompleted: {
        console.log("AutoLabel main window loaded")
    }
}
