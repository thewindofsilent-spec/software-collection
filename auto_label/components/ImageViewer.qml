import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: imageViewer
    color: "#2d2d2d"
    clip: true

    property real scaleFactor: 1.0
    property real minScale: 0.1
    property real maxScale: 10.0
    property point panOffset: Qt.point(0, 0)
    property bool isPanning: false
    property point panStart: Qt.point(0, 0)
    property point lastMouse: Qt.point(0, 0)

    property int imageWidth: controller.getImageWidth()
    property int imageHeight: controller.getImageHeight()

    signal shapeSelected(int index)

    Rectangle {
        id: canvasContainer
        anchors.centerIn: parent
        width: imageViewer.width * scaleFactor
        height: imageViewer.height * scaleFactor
        color: "#1a1a1a"
        transform: Translate {
            x: panOffset.x
            y: panOffset.y
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

                        var scaleX = annotationCanvas.width / (imageWidth || 1)
                        var scaleY = annotationCanvas.height / (imageHeight || 1)

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
                                        points[0][0] * scaleX,
                                        points[0][1] * scaleY,
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
                    id: canvasMouseArea
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

                    onPressed: {
                        if (mouse.button === Qt.MiddleButton || (mouse.button === Qt.LeftButton && mouse.modifiers & Qt.ShiftModifier)) {
                            isPanning = true
                            panStart = mouse
                            lastMouse = mouse
                        }
                    }

                    onReleased: {
                        isPanning = false
                    }

                    onPositionChanged: {
                        if (isPanning) {
                            panOffset.x += mouse.x - lastMouse.x
                            panOffset.y += mouse.y - lastMouse.y
                            lastMouse = mouse
                        }
                    }

                    onWheel: {
                        var delta = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                        var newScale = scaleFactor * delta
                        if (newScale >= minScale && newScale <= maxScale) {
                            var mouseX = wheel.x
                            var mouseY = wheel.y

                            var oldScale = scaleFactor
                            scaleFactor = newScale

                            panOffset.x = mouseX - (mouseX - panOffset.x) * (newScale / oldScale)
                            panOffset.y = mouseY - (mouseY - panOffset.y) * (newScale / oldScale)
                        }
                    }

                    onClicked: {
                        if (mouse.button === Qt.LeftButton && !(mouse.modifiers & Qt.ShiftModifier)) {
                            var scaleX = annotationCanvas.width / (imageWidth || 1)
                            var scaleY = annotationCanvas.height / (imageHeight || 1)

                            var relX = mouse.x / scaleX
                            var relY = mouse.y / scaleY

                            var shapeIndex = findShapeAtPosition(relX, relY)
                            if (shapeIndex >= 0) {
                                shapeSelected(shapeIndex)
                            }
                        }
                    }

                    onDoubleClicked: {
                        if (mouse.button === Qt.RightButton) {
                            contextMenu.popup()
                        }
                    }
                }
            }
        }
    }

    Menu {
        id: contextMenu
        MenuItem {
            text: "Add Rectangle"
            onTriggered: addRectangleAtPoint(lastMouse.x, lastMouse.y)
        }
        MenuItem {
            text: "Add Point"
            onTriggered: addPointAtPosition(lastMouse.x, lastMouse.y)
        }
    }

    function findShapeAtPosition(x, y) {
        var shapes = []
        for (var i = 0; i < controller.getShapeCount(); i++) {
            var shape = controller.getShape(i)
            if (shape) shapes.push(shape)
        }

        for (var i = 0; i < shapes.length; i++) {
            var shape = shapes[i]
            if (shape.shapeType === "rectangle") {
                var points = shape.points
                if (points.length >= 2) {
                    var x1 = Math.min(points[0][0], points[1][0])
                    var y1 = Math.min(points[0][1], points[1][1])
                    var x2 = Math.max(points[0][0], points[1][0])
                    var y2 = Math.max(points[0][1], points[1][1])
                    if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
                        return i
                    }
                }
            } else if (shape.shapeType === "point") {
                var points = shape.points
                if (points.length >= 1) {
                    var dist = Math.sqrt(Math.pow(x - points[0][0], 2) + Math.pow(y - points[0][1], 2))
                    if (dist < 10) {
                        return i
                    }
                }
            }
        }
        return -1
    }

    function addRectangleAtPoint(mouseX, mouseY) {
        var scaleX = annotationCanvas.width / (imageWidth || 1)
        var scaleY = annotationCanvas.height / (imageHeight || 1)
        var relX = mouseX / scaleX
        var relY = mouseY / scaleY

        var x1 = Math.max(0, relX - 50)
        var y1 = Math.max(0, relY - 50)
        var x2 = Math.min(imageWidth, relX + 50)
        var y2 = Math.min(imageHeight, relY + 50)

        controller.addRectangle(controller.imageListModel.selectedIndex, "object", x1, y1, x2, y2)
        annotationCanvas.requestPaint()
    }

    function addPointAtPosition(mouseX, mouseY) {
        var scaleX = annotationCanvas.width / (imageWidth || 1)
        var scaleY = annotationCanvas.height / (imageHeight || 1)
        var relX = mouseX / scaleX
        var relY = mouseY / scaleY

        var label = "0"
        var existingPoints = 0
        for (var i = 0; i < controller.getShapeCount(); i++) {
            var shape = controller.getShape(i)
            if (shape && shape.shapeType === "point") {
                existingPoints++
            }
        }
        label = String(existingPoints)

        controller.addPoint(controller.imageListModel.selectedIndex, label, relX, relY)
        annotationCanvas.requestPaint()
    }

    function resetView() {
        scaleFactor = 1.0
        panOffset = Qt.point(0, 0)
    }

    Connections {
        target: controller
        function onAnnotationChanged() {
            annotationCanvas.requestPaint()
        }
    }
}
