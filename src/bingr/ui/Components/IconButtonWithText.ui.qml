import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    height: 40

    property int btnRadius: 20
    property int btnImageSize: 32
    property int btnShadowSpread: 4
    property int btnShadowBlur: 4
    property string btnTooptipText: qsTr("Click to add channels.")
    property string btnText: qsTr("Add Channels")
    property int btnTextSize: 14
    property url btnImageSource: Qt.resolvedUrl("../images/plus-circle.svg")

    //implicit width of button = image left margin + width of image + text left margin + text implicit width + 8 (text rigth margin)
    implicitWidth: iconBtnImage.anchors.leftMargin + iconBtnImage.implicitWidth
                   + iconBtnText.anchors.leftMargin + iconBtnText.implicitWidth

    // properties

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: iconBtnRect
        anchors.fill: parent
        color: Constants.backgroundColor
        radius: root.btnRadius
        border.width: 0

        DesignEffect {
            effects: [
                DesignDropShadow {
                    id: dropShadow
                    //color: "#3f545454"
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
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: Math.ceil(
                                    (root.btnRadius - (root.btnImageSize / 2)) + 2)
            source: root.btnImageSource
            sourceSize.width: 36
            sourceSize.height: 36
            fillMode: Image.PreserveAspectFit
        }

        Text {
            id: iconBtnText
            color: "#e7e7e7"
            height: parent.height
            anchors.left: iconBtnImage.right
            anchors.leftMargin: iconBtnImage.anchors.leftMargin
            anchors.verticalCenter: iconBtnImage.verticalCenter
            text: root.btnText
            font.pixelSize: root.btnTextSize
            verticalAlignment: Text.AlignVCenter
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
                    iconBtnRect.scale = 0.9
                }
            }

            Connections {
                target: mouseArea
                function onReleased() {
                    iconBtnRect.scale = 1.0
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
