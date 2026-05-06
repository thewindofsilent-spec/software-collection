import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: fileList
    color: "#1e1e1e"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredHeight: 36
            Layout.fillWidth: true
            color: "#2d2d2d"

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                spacing: 10

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Images (" + imageListModel.count + ")"
                    color: "#cccccc"
                    font.pixelSize: 13
                    font.bold: true
                }
            }

            Button {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 10
                width: 80
                height: 24
                text: "Refresh"
                onClicked: {
                    if (controller.currentDir) {
                        controller.loadFolder(controller.currentDir)
                    }
                }
            }
        }

        ListView {
            id: imageListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: imageListModel
            clip: true
            currentIndex: imageListModel.selectedIndex
            focus: true

            delegate: Rectangle {
                width: parent ? parent.width : 0
                height: 64
                color: ListView.isCurrentItem ? "#094771" : (modelData.annotated ? "#2d4a2d" : "transparent")
                border.width: ListView.isCurrentItem ? 1 : 0
                border.color: "#0078d4"

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    padding: 10

                    Rectangle {
                        width: 48
                        height: 48
                        color: "#333333"
                        radius: 4

                        Image {
                            anchors.fill: parent
                            source: "image://imageProvider/" + modelData.path
                            fillMode: Image.PreserveAspectCrop
                            smooth: true
                            cache: false
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

                        Row {
                            spacing: 6

                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: modelData.annotated ? "#4ec94e" : "#888888"
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: modelData.annotated ? "Annotated" : "Pending"
                                color: modelData.annotated ? "#4ec94e" : "#888888"
                                font.pixelSize: 11
                            }
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
                width: 10
                policy: ScrollBar.AsNeeded
            }
        }
    }

    Rectangle {
        id: loadingOverlay
        anchors.fill: parent
        color: "#80000000"
        visible: false

        Column {
            anchors.centerIn: parent
            spacing: 10

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: loadingOverlay.visible
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Loading..."
                color: "#ffffff"
                font.pixelSize: 14
            }
        }
    }
}
