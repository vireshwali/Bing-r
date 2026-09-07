import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    height: 36
    width: height

    // properties
    property int btnImageSize: 26
    property int btnShadowSpread: 4
    property int btnShadowBlur: 4
    property url btnImageSource: Qt.resolvedUrl("../images/plus-circle.svg")
    property string btnTooptipText: qsTr("Click to add channels.")

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: iconBtnRect
        anchors.fill: parent
        color: Constants.backgroundColor
        radius: root.width / 2
        border.width: 0

        DesignEffect {
            effects: [
                DesignDropShadow {
                    id: dropShadow
                    color: "#3f3b3b3b"
                    spread: root.btnShadowSpread
                    blur: root.btnShadowBlur
                    offsetY: 1
                }
            ]
        }

        Image {
            id: iconBtnImage
            width: root.btnImageSize
            height: root.btnImageSize
            anchors.centerIn: parent
            source: root.btnImageSource
            sourceSize.width: 28
            sourceSize.height: 28
            fillMode: Image.PreserveAspectFit
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            scale: 1
            hoverEnabled: true

            // Tooltip for the menu item
            ToolTip.delay: Constants.defaultTooltipDelay
            ToolTip.timeout: Constants.defaultTooltipTimeout
            ToolTip.visible: mouseArea.containsMouse
            ToolTip.text: root.btnTooptipText

            Connections {
                target: mouseArea
                function onPressed() {
                    iconBtnRect.scale = 0.9;
                }
            }

            Connections {
                target: mouseArea
                function onReleased() {
                    iconBtnRect.scale = 1.0;
                }
            }
        }
    }

    states: [
        State {
            name: "Mouse_Entered"
            when: mouseArea.containsMouse
            PropertyChanges {
                target: iconBtnRect
                color: dropShadow.color
            }
        },
        State {
            name: "Mouse_Exited"
            when: !mouseArea.containsMouse
            PropertyChanges {
                target: iconBtnRect
                color: Constants.backgroundColor
            }
        }
    ]
}
