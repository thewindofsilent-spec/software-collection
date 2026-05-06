import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: autoLabelDialog
    title: "Auto Label with YOLO"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    width: 450
<<<<<<< HEAD
    height: 420
=======
    height: 350
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55

    property string sourceDir: ""
    property string outputDir: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Text {
            text: "Automatic Labeling Configuration"
            font.pixelSize: 16
            font.bold: true
            color: "#ffffff"
        }

        ColumnLayout {
            spacing: 10

            Row {
                spacing: 10
                Layout.fillWidth: true

                Label {
                    text: "Source Images:"
                    color: "#cccccc"
                    Layout.preferredWidth: 100
                }

                TextField {
                    id: sourceField
                    placeholderText: "Select image folder"
                    text: sourceDir
                    Layout.fillWidth: true
                }

                Button {
                    text: "Browse"
                    onClicked: sourceFolderDialog.open()
                }
            }

            Row {
                spacing: 10
                Layout.fillWidth: true

                Label {
                    text: "Output Folder:"
                    color: "#cccccc"
                    Layout.preferredWidth: 100
                }

                TextField {
                    id: outputField
                    placeholderText: "Select output folder"
                    text: outputDir
                    Layout.fillWidth: true
                }

                Button {
                    text: "Browse"
                    onClicked: outputFolderDialog.open()
                }
            }
        }

        GridLayout {
            columns: 2
            columnSpacing: 15
            rowSpacing: 10

            Label {
                text: "Confidence:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            Row {
                spacing: 5
                Layout.fillWidth: true

                Slider {
                    id: confSlider
                    from: 0.01
                    to: 1.0
                    value: 0.25
                    stepSize: 0.01
                    Layout.fillWidth: true
                }

                Text {
                    text: confSlider.value.toFixed(2)
                    color: "#ffffff"
                    Layout.preferredWidth: 50
                }
            }

            Label {
                text: "IoU:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            Row {
                spacing: 5
                Layout.fillWidth: true

                Slider {
                    id: iouSlider
                    from: 0.01
                    to: 1.0
                    value: 0.45
                    stepSize: 0.01
                    Layout.fillWidth: true
                }

                Text {
                    text: iouSlider.value.toFixed(2)
                    color: "#ffffff"
                    Layout.preferredWidth: 50
                }
            }

            Label {
                text: "Max Detections:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: maxDetSpin
                from: 1
                to: 1000
                value: 300
                Layout.fillWidth: true
            }
<<<<<<< HEAD

            Label {
                text: "Detect Keypoints:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            CheckBox {
                id: detectKeypointsCheck
                checked: true
            }

            Label {
                text: "Keypoint Conf:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            Row {
                spacing: 5
                Layout.fillWidth: true

                Slider {
                    id: keypointConfSlider
                    from: 0.01
                    to: 1.0
                    value: 0.25
                    stepSize: 0.01
                    Layout.fillWidth: true
                    enabled: detectKeypointsCheck.checked
                }

                Text {
                    text: keypointConfSlider.value.toFixed(2)
                    color: "#ffffff"
                    Layout.preferredWidth: 50
                }
            }
=======
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#444444"
        }

        Row {
            spacing: 10
            Layout.alignment: Qt.AlignRight

            ProgressBar {
                id: autoLabelProgress
                width: 200
                height: 20
                visible: controller.isAutoLabeling
                value: controller.autoLabelProgress
            }

            Text {
                text: controller.isAutoLabeling ? "Processing..." : "Ready"
                color: controller.isAutoLabeling ? "#4ec94e" : "#888888"
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Label {
            id: statusLabel
            Layout.fillWidth: true
            color: "#888888"
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }
    }

    FolderDialog {
        id: sourceFolderDialog
        title: "Select Source Image Folder"
        onAccepted: {
            sourceDir = sourceFolderDialog.currentFolder
            sourceField.text = sourceDir
            if (!outputDir) {
                outputDir = sourceDir + "/auto_labeled"
                outputField.text = outputDir
            }
        }
    }

    FolderDialog {
        id: outputFolderDialog
        title: "Select Output Folder"
        onAccepted: {
            outputDir = outputFolderDialog.currentFolder
            outputField.text = outputDir
        }
    }

    onAccepted: {
        if (!controller.modelLoaded) {
            statusLabel.text = "Please load a model first"
            return
        }

        if (!sourceDir) {
            statusLabel.text = "Please select source image folder"
            return
        }

        controller.startAutoLabel(
            sourceDir,
            outputDir,
            confSlider.value,
            iouSlider.value,
<<<<<<< HEAD
            maxDetSpin.value,
            detectKeypointsCheck.checked,
            keypointConfSlider.value
=======
            maxDetSpin.value
>>>>>>> 60c7948fc72e4c8b19848527e72c3430dbdb4c55
        )
    }

    Connections {
        target: controller
        function onAutoLabelFinished(successCount, total) {
            statusLabel.text = "Completed: " + successCount + " / " + total + " images labeled"
        }
    }
}
