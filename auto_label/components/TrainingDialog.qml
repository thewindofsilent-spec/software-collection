import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: trainingDialog
    title: "Train YOLO Model"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    width: 500
    height: 450

    property string dataYaml: ""
    property string projectDir: "runs/detect"
    property string runName: "train"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Text {
            text: "YOLO Training Configuration"
            font.pixelSize: 16
            font.bold: true
            color: "#ffffff"
        }

        GridLayout {
            columns: 2
            columnSpacing: 15
            rowSpacing: 10

            Label {
                text: "Data YAML:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            Row {
                spacing: 5
                Layout.fillWidth: true

                TextField {
                    id: dataYamlField
                    placeholderText: "path/to/dataset.yaml"
                    Layout.fillWidth: true
                    text: dataYaml
                }

                Button {
                    text: "Browse"
                    onClicked: dataYamlDialog.open()
                }
            }

            Label {
                text: "Epochs:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: epochsSpin
                from: 1
                to: 1000
                value: 100
                stepSize: 10
                Layout.fillWidth: true
            }

            Label {
                text: "Batch Size:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: batchSpin
                from: 1
                to: 128
                value: 16
                stepSize: 4
                Layout.fillWidth: true
            }

            Label {
                text: "Image Size:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: imgszSpin
                from: 320
                to: 1280
                value: 640
                stepSize: 32
                Layout.fillWidth: true
            }

            Label {
                text: "Workers:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: workersSpin
                from: 1
                to: 32
                value: 8
                stepSize: 1
                Layout.fillWidth: true
            }

            Label {
                text: "Patience:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            SpinBox {
                id: patienceSpin
                from: 5
                to: 200
                value: 50
                stepSize: 5
                Layout.fillWidth: true
            }

            Label {
                text: "Device:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            ComboBox {
                id: deviceCombo
                model: ["0", "1", "2", "3", "cpu"]
                Layout.fillWidth: true
            }

            Label {
                text: "Project:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            TextField {
                id: projectField
                placeholderText: "runs/detect"
                text: projectDir
                Layout.fillWidth: true
            }

            Label {
                text: "Name:"
                color: "#cccccc"
                Layout.alignment: Qt.AlignRight
            }

            TextField {
                id: nameField
                placeholderText: "train"
                text: runName
                Layout.fillWidth: true
            }
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
                id: trainingProgress
                width: 200
                height: 20
                visible: controller.isTraining
                value: controller.trainProgress
            }

            Text {
                text: controller.isTraining ? "Training..." : "Ready"
                color: controller.isTraining ? "#4ec94e" : "#888888"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    FileDialog {
        id: dataYamlDialog
        title: "Select Dataset YAML"
        nameFilters: ["YAML Files (*.yaml *.yml)", "All Files (*)"]
        onAccepted: {
            dataYaml = dataYamlDialog.currentFile
            dataYamlField.text = dataYaml
        }
    }

    onAccepted: {
        if (!controller.modelLoaded) {
            trainingDialog.visible = false
            return
        }

        controller.startTraining(
            dataYaml || dataYamlField.text,
            epochsSpin.value,
            batchSpin.value,
            imgszSpin.value,
            workersSpin.value,
            patienceSpin.value,
            projectField.text,
            nameField.text
        )
    }

    onVisibleChanged: {
        if (visible && !controller.modelLoaded) {
            statusLabel.text = "Please load a model first"
        } else {
            statusLabel.text = ""
        }
    }

    Label {
        id: statusLabel
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter
        color: "#ff6666"
        font.pixelSize: 12
    }

    Connections {
        target: controller
        function onTrainingFinished(modelPath) {
            if (modelPath) {
                trainingDialog.close()
            }
        }
    }
}
