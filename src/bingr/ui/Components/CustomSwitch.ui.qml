

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui

Item {
    id: root
    width: switchControl.width
    height: switchControl.height

    property string switchText: ""
    property int controlHeight: 18
    property int controlWidth: 64

    property alias checked: switchControl.checked

    Switch {
        id: switchControl
        anchors.centerIn: parent
        display: AbstractButton.IconOnly
        text: root.switchText
        checked: false

        indicator: Rectangle {
            id: bgRect
            implicitWidth: root.controlWidth
            implicitHeight: root.controlHeight
            x: switchControl.leftPadding
            y: parent.height / 2 - height / 2
            radius: 12
            color: switchControl.checked ? Constants.accent : Constants.textColorMuted
            border.color: switchControl.checked ? Constants.accent : Constants.textColorMuted

            Rectangle {
                id: toggleHandle
                //x: control.checked ? parent.width - width : 0
                width: root.controlHeight
                height: root.controlHeight
                radius: root.controlHeight / 2
                color: switchControl.down ? "#cccccc" : "#ffffff"
                border.color: switchControl.checked ? (switchControl.down ? "#17a81a" : "#21be2b") : "#999999"
            }
        }

        contentItem: Text {
            text: switchControl.text
            font: switchControl.font
            opacity: enabled ? 1.0 : 0.3
            color: switchControl.down ? "#17a81a" : "#21be2b"
            verticalAlignment: Text.AlignVCenter
            leftPadding: switchControl.indicator.width + switchControl.spacing
        }
    }
    states: [
        State {
            name: "UnChecked"
            when: !switchControl.checked
            PropertyChanges {
                target: toggleHandle
                x: 0
            }
        },
        State {
            name: "Checked"
            when: switchControl.checked
            PropertyChanges {
                target: toggleHandle
                x: bgRect.width - toggleHandle.width
            }
        }
    ]
    transitions: [
        Transition {
            id: transition
            ParallelAnimation {
                SequentialAnimation {
                    PauseAnimation {
                        duration: 0
                    }

                    PropertyAnimation {
                        target: toggleHandle
                        property: "x"
                        easing.bezierCurve: [0.23, 1, 0.32, 1, 1, 1]
                        duration: 400
                    }
                }
            }
            to: "*"
            from: "*"
        }
    ]
}
