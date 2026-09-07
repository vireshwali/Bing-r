/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import QtQuick.Studio.DesignEffects
import ui

Item {
    id: root
    width: 165
    height: 40

    // properties
    property url menuImageSource: Qt.resolvedUrl("../images/user.svg")
    property string menuText: qsTr("Home")
    property string menuTooltipText: qsTr("Go to Home.")
    property double fontLetterSpacing: 1.0

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: rectangle
        color: Constants.barBackgroundColorLeftNav
        anchors.fill: parent

        Rectangle {
            id: buttonRect
            anchors.fill: parent
            z: 6
            color: Constants.barBackgroundColorLeftNav
            radius: 6
            border.width: 0

            DesignEffect {
                effects: [
                    DesignDropShadow {
                        id: designDropShadow
                        visible: true
                        color: "#517d5d30"
                        showBehind: true
                        offsetX: 0
                        offsetY: 0
                        spread: 6
                        blur: 10
                    }
                ]
            }

            Image {
                id: buttonIconImage
                width: 32
                height: 32
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                source: root.menuImageSource
                sourceSize.height: 36
                sourceSize.width: 36
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: buttonLabel
                height: 32
                color: "#e7e7e7"
                text: root.menuText
                anchors.verticalCenter: buttonIconImage.verticalCenter
                anchors.left: buttonIconImage.right
                anchors.leftMargin: 12
                font.letterSpacing: root.fontLetterSpacing
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
                font.styleName: "Medium"
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true

                // Tooltip for the menu item
                ToolTip.delay: Constants.defaultTooltipDelay
                ToolTip.timeout: Constants.defaultTooltipTimeout
                ToolTip.visible: mouseArea.containsMouse
                ToolTip.text: root.menuTooltipText
            }
        }
    }
    states: [
        State {
            name: "Mouse_Entered"
            when: mouseArea.containsMouse
            PropertyChanges {
                target: buttonRect
                color: "#292929"
            }
        },
        State {
            name: "Mouse_Exited"
            when: !mouseArea.containsMouse
            PropertyChanges {
                target: buttonRect
                color: Constants.barBackgroundColorLeftNav
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
                        target: buttonRect
                        property: "color"
                        easing.bezierCurve: [0.215, 0.61, 0.355, 1, 1, 1]
                        duration: 400
                    }
                }
            }
            to: "*"
            from: "*"
        }
    ]
}
