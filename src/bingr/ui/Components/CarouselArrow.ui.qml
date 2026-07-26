
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import ui

Item {
    id: root
    width: 38
    height: 120

    property string direction: "left"
    property bool arrowEnabled: true
    property real defaultOpacity: 0.5
    property real hoverOpacity: 1.0

    property alias buttonMouseArea: arrowMouseArea

    Rectangle {
        id: arrowBg
        anchors.fill: parent
        radius: width / 2
        color: Constants.barBackgroundColorLeftNav
        opacity: arrowMouseArea.containsMouse ? root.hoverOpacity : root.defaultOpacity
        visible: root.arrowEnabled

        Image {
            id: arrowImg
            anchors.centerIn: parent
            mipmap: true
            fillMode: Image.PreserveAspectFit
            source: "../images/arrow-fat-line-left.svg"
            sourceSize.width: 40
            sourceSize.height: 40
            width: 32
            height: 32
        }

        MouseArea {
            id: arrowMouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            enabled: root.arrowEnabled
        }
    }

    states: [
        State {
            name: "Left_Image"
            when: root.direction === "left"
            PropertyChanges {
                target: arrowImg
                source: "../images/arrow-fat-line-left.svg"
            }
        },
        State {
            name: "Right_Image"
            when: root.direction === "right"
            PropertyChanges {
                target: arrowImg
                source: "../images/arrow-fat-line-right.svg"
            }
        }
    ]
}
