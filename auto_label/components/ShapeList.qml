import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: shapeList
    color: "#1e1e1e"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredHeight: 36
            Layout.fillWidth: true
            color: "#2d2d2d"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Shapes (" + controller.getShapeCount() + ")"
                color: "#cccccc"
                font.pixelSize: 13
                font.bold: true
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 10
                spacing: 8

                Button {
                    width: 28
                    height: 28
                    text: "+"
                    font.pixelSize: 16
                    onClicked: rectDialog.open()
                }

                Button {
                    width: 28
                    height: 28
                    text: "·"
                    font.pixelSize: 16
                    onClicked: pointDialog.open()
                }
            }
        }

        ListView {
            id: shapesListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: shapeListModel
            currentIndex: -1

            delegate: Rectangle {
                width: parent ? parent.width : 0
                height: 70
                color: ListView.isCurrentItem ? "#094771" : "#252526"
                border.width: ListView.isCurrentItem ? 1 : 0
                border.color: "#0078d4"

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
                            color: modelData.shapeType === "rectangle" ? "#00ff00" : "#ff4444"
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.label || "Unnamed"
                            color: "#ffffff"
                            font.pixelSize: 13
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.shapeType === "rectangle" ? "[Rectangle]" : "[Point]"
                            color: "#888888"
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        text: {
                            if (modelData.shapeType === "rectangle") {
                                var pts = modelData.points
                                if (pts && pts.length >= 2) {
                                    return "From (" + pts[0][0].toFixed(0) + ", " + pts[0][1].toFixed(0) +
                                           ") To (" + pts[1][0].toFixed(0) + ", " + pts[1][1].toFixed(0) + ")"
                                }
                            } else {
                                var pts = modelData.points
                                if (pts && pts.length >= 1) {
                                    return "At (" + pts[0][0].toFixed(0) + ", " + pts[0][1].toFixed(0) + ")"
                                }
                            }
                            return ""
                        }
                        color: "#aaaaaa"
                        font.pixelSize: 10
                    }

                    Row {
                        spacing: 5

                        Button {
                            text: "Edit"
                            width: 50
                            height: 22
                            font.pixelSize: 10
                            onClicked: {
                                shapesListView.currentIndex = index
                                editShape(index)
                            }
                        }

                        Button {
                            text: "Delete"
                            width: 50
                            height: 22
                            font.pixelSize: 10
                            onClicked: {
                                controller.removeShape(controller.controller.imageListModel.selectedIndex, index)
                                refreshShapeList()
                            }
                        }
                    }
                }
            }

            ScrollBar.vertical: ScrollBar {
                active: true
                width: 10
            }
        }
    }

    ListModel {
        id: shapeListModel
    }

    Dialog {
        id: rectDialog
        title: "Add Rectangle"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true

        ColumnLayout {
            spacing: 10

            Label { text: "Label:" }
            TextField {
                id: rectLabelField
                placeholderText: "Enter label"
                Layout.fillWidth: true
            }

            Label { text: "X1:" }
            TextField {
                id: x1Field
                placeholderText: "0"
                Layout.fillWidth: true
            }

            Label { text: "Y1:" }
            TextField {
                id: y1Field
                placeholderText: "0"
                Layout.fillWidth: true
            }

            Label { text: "X2:" }
            TextField {
                id: x2Field
                placeholderText: "100"
                Layout.fillWidth: true
            }

            Label { text: "Y2:" }
            TextField {
                id: y2Field
                placeholderText: "100"
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            var label = rectLabelField.text || "object"
            var x1 = parseFloat(x1Field.text) || 0
            var y1 = parseFloat(y1Field.text) || 0
            var x2 = parseFloat(x2Field.text) || 100
            var y2 = parseFloat(y2Field.text) || 100

            controller.addRectangle(controller.imageListModel.selectedIndex, label, x1, y1, x2, y2)
            refreshShapeList()
        }
    }

    Dialog {
        id: pointDialog
        title: "Add Point"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true

        ColumnLayout {
            spacing: 10

            Label { text: "Label (keypoint index):" }
            TextField {
                id: pointLabelField
                placeholderText: "0"
                Layout.fillWidth: true
            }

            Label { text: "X:" }
            TextField {
                id: pxField
                placeholderText: "0"
                Layout.fillWidth: true
            }

            Label { text: "Y:" }
            TextField {
                id: pyField
                placeholderText: "0"
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            var label = pointLabelField.text || "0"
            var x = parseFloat(pxField.text) || 0
            var y = parseFloat(pyField.text) || 0

            controller.addPoint(controller.imageListModel.selectedIndex, label, x, y)
            refreshShapeList()
        }
    }

    function refreshShapeList() {
        shapeListModel.clear()
        var count = controller.getShapeCount()
        for (var i = 0; i < count; i++) {
            var shape = controller.getShape(i)
            if (shape) {
                shapeListModel.append({
                    index: i,
                    label: shape.label,
                    shapeType: shape.shapeType,
                    points: shape.points
                })
            }
        }
    }

    function editShape(index) {
        var shape = controller.getShape(index)
        if (!shape) return

        if (shape.shapeType === "rectangle") {
            rectLabelField.text = shape.label
            if (shape.points.length >= 2) {
                x1Field.text = shape.points[0][0]
                y1Field.text = shape.points[0][1]
                x2Field.text = shape.points[1][0]
                y2Field.text = shape.points[1][1]
            }
            rectDialog.onAccepted.disconnect()
            rectDialog.onAccepted.connect(function() {
                var label = rectLabelField.text || "object"
                var x1 = parseFloat(x1Field.text) || 0
                var y1 = parseFloat(y1Field.text) || 0
                var x2 = parseFloat(x2Field.text) || 100
                var y2 = parseFloat(y2Field.text) || 100
                controller.updateRectangle(controller.imageListModel.selectedIndex, index, label, x1, y1, x2, y2)
                refreshShapeList()
            })
            rectDialog.open()
        } else {
            pointLabelField.text = shape.label
            if (shape.points.length >= 1) {
                pxField.text = shape.points[0][0]
                pyField.text = shape.points[0][1]
            }
            pointDialog.onAccepted.disconnect()
            pointDialog.onAccepted.connect(function() {
                var label = pointLabelField.text || "0"
                var x = parseFloat(pxField.text) || 0
                var y = parseFloat(pyField.text) || 0
                controller.updatePoint(controller.imageListModel.selectedIndex, index, label, x, y)
                refreshShapeList()
            })
            pointDialog.open()
        }
    }

    Connections {
        target: controller
        function onAnnotationChanged() {
            refreshShapeList()
        }
    }
}
