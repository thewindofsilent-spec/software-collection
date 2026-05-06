import QtQuick 6.5
import QtQuick.Controls 6.5
import QtQuick.Layouts 6.5
import QtQuick.Window 6.5
import QtQuick.Controls.Basic 6.5
import VideoToPicture 1.0

ApplicationWindow {
    id: root
    width: 800
    height: 650
    visible: true
    title: "视频转图片"
    color: "#0f0f23"

    // Backend
    VideoToPicture {
        id: backend
    }

    // Drag and drop wrapper
    DropArea {
        id: dropArea
        anchors.fill: parent
        onDropped: (drag) => {
            if (drag.urls.length > 0) {
                backend.selectVideo(drag.urls[0])
            }
        }
    }

    // Main content
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        anchors.topMargin: 16
        spacing: 20

        // Title
        Label {
            text: "视频转图片"
            font.pixelSize: 24
            font.weight: Font.Bold
            color: "#ffffff"
            Layout.alignment: Qt.AlignHCenter
        }

        // Drop zone
        Rectangle {
            id: dropZone
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            color: dropArea.containsDrag ? "#16213e" : "#1a1a2e"
            border.width: 2
            border.color: dropArea.containsDrag ? "#4fc3f7" : "#2a2a4e"
            radius: 16

            Behavior on border.color { PropertyAnimation { duration: 200 } }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8

                Label {
                    text: "拖拽视频文件到此处"
                    color: "#8888aa"
                    font.pixelSize: 14
                    Layout.alignment: Qt.AlignHCenter
                }

                Label {
                    text: backend.videoPath || "点击按钮选择视频"
                    color: backend.videoPath ? "#4fc3f7" : "#555577"
                    font.pixelSize: 12
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 600
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: backend.selectVideo("")
            }
        }

        // Settings card
        Rectangle {
            Layout.fillWidth: true
            color: "#1a1a2e"
            radius: 16

            ColumnLayout {
                anchors.margins: 20
                spacing: 16

                Label {
                    text: "提取设置"
                    color: "#ffffff"
                    font.pixelSize: 16
                    font.weight: Font.Bold
                }

                GridLayout {
                    columns: 2
                    rowSpacing: 16
                    columnSpacing: 24

                    // Frame interval
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "帧间隔"
                            color: "#8888aa"
                            font.pixelSize: 12
                        }

                        RowLayout {
                            spacing: 8

                            TextField {
                                id: txtInterval
                                text: "30"
                                Layout.preferredWidth: 100
                                Layout.preferredHeight: 40
                                color: "#ffffff"
                                placeholderText: "30"
                                background: Rectangle {
                                    color: "#0f0f23"
                                    radius: 8
                                    border.color: txtInterval.focus ? "#4fc3f7" : "#2a2a4e"
                                    border.width: 1
                                }
                                horizontalAlignment: TextInput.AlignHCenter
                            }

                            Label {
                                text: "帧"
                                color: "#666688"
                                font.pixelSize: 13
                            }
                        }
                    }

                    // Start frame
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "起始帧"
                            color: "#8888aa"
                            font.pixelSize: 12
                        }

                        RowLayout {
                            spacing: 8

                            TextField {
                                id: txtStart
                                text: "0"
                                Layout.preferredWidth: 100
                                Layout.preferredHeight: 40
                                color: "#ffffff"
                                placeholderText: "0"
                                background: Rectangle {
                                    color: "#0f0f23"
                                    radius: 8
                                    border.color: txtStart.focus ? "#4fc3f7" : "#2a2a4e"
                                    border.width: 1
                                }
                                horizontalAlignment: TextInput.AlignHCenter
                            }

                            Label {
                                text: "帧"
                                color: "#666688"
                                font.pixelSize: 13
                            }
                        }
                    }

                    // End frame
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "结束帧"
                            color: "#8888aa"
                            font.pixelSize: 12
                        }

                        RowLayout {
                            spacing: 8

                            TextField {
                                id: txtEnd
                                text: "0"
                                Layout.preferredWidth: 100
                                Layout.preferredHeight: 40
                                color: "#ffffff"
                                placeholderText: "0"
                                background: Rectangle {
                                    color: "#0f0f23"
                                    radius: 8
                                    border.color: txtEnd.focus ? "#4fc3f7" : "#2a2a4e"
                                    border.width: 1
                                }
                                horizontalAlignment: TextInput.AlignHCenter
                            }

                            Label {
                                text: "帧 (0=结束)"
                                color: "#666688"
                                font.pixelSize: 12
                            }
                        }
                    }

                    // Image format
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "图片格式"
                            color: "#8888aa"
                            font.pixelSize: 12
                        }

                        ComboBox {
                            id: cmbFormat
                            model: ["PNG", "JPEG", "BMP"]
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 40
                            currentIndex: 0

                            background: Rectangle {
                                color: "#0f0f23"
                                radius: 8
                                border.color: "#2a2a4e"
                                border.width: 1
                            }

                            contentItem: Label {
                                text: cmbFormat.currentText
                                color: "#ffffff"
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                            }
                        }
                    }
                }
            }
        }

        // Output folder
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                id: btnOutput
                text: "选择输出目录"
                Layout.preferredHeight: 44
                Layout.preferredWidth: 140

                background: Rectangle {
                    color: "#2a2a4e"
                    radius: 8
                }

                contentItem: Label {
                    text: parent.text
                    color: "#ffffff"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                }

                onClicked: backend.selectOutput("")
            }

            Label {
                text: backend.outputPath || "未选择"
                color: backend.outputPath ? "#4fc3f7" : "#555566"
                font.pixelSize: 13
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }

        // Progress section
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: backend.extracting

            ProgressBar {
                id: progressBar
                Layout.fillWidth: true
                Layout.preferredHeight: 10
                from: 0
                to: Math.max(backend.progressTotal, 1)
                value: backend.progressCurrent

                background: Rectangle {
                    color: "#2a2a4e"
                    radius: 5
                }

                contentItem: Rectangle {
                    color: "#4fc3f7"
                    radius: 5
                }
            }

            Label {
                text: backend.progressCurrent + " / " + backend.progressTotal + " 帧"
                color: "#8888aa"
                font.pixelSize: 12
                Layout.alignment: Qt.AlignHCenter
            }
        }

        // Log area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 100
            color: "#0d0d1a"
            radius: 12
            border.color: "#1e1e32"
            border.width: 1

            ScrollView {
                anchors.fill: parent
                anchors.margins: 12

                TextArea {
                    id: logArea
                    text: backend.logText
                    color: "#7fcd91"
                    font.family: "Consolas"
                    font.pixelSize: 12
                    readOnly: true
                    background: Rectangle { color: "transparent" }
                    wrapMode: TextArea.Wrap
                }
            }
        }

        // Extract button
        Button {
            id: btnExtract
            text: backend.extracting ? "提取中..." : "开始提取"
            Layout.fillWidth: true
            Layout.preferredHeight: 54

            background: Rectangle {
                color: backend.extracting ? "#357ae8" : (backend.videoPath && backend.outputPath ? "#4fc3f7" : "#2a2a4e")
                radius: 12

                SequentialAnimation on color {
                    running: backend.extracting
                    loops: Animation.Infinite
                    ColorAnimation { from: "#4fc3f7"; to: "#357ae8"; duration: 600 }
                    ColorAnimation { from: "#357ae8"; to: "#4fc3f7"; duration: 600 }
                }
            }

            contentItem: Label {
                text: parent.text
                color: backend.videoPath && backend.outputPath ? (backend.extracting ? "#ffffff" : "#0f0f23") : "#555566"
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 16
                font.weight: Font.Bold
            }

            onClicked: {
                if (!backend.extracting) {
                    backend.startExtract(
                        parseInt(txtInterval.text),
                        parseInt(txtStart.text),
                        parseInt(txtEnd.text),
                        cmbFormat.currentText.toUpperCase()
                    )
                }
            }
        }
    }
}