import QtQuick
import QtQuick.Controls
import ui

Item {
    id: root
    width: 36
    height: 36

    // properties
    readonly property url menuImageSource: Qt.resolvedUrl("../images/arrows-collapse.svg")
    readonly property double menuImageOpacityDefault: 0.5

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: bgRect
        anchors.fill: parent
        color: "#b65a1c"
        radius: 18
        border.width: 0

        Image {
            id: collapseIconImage
            width: 26
            height: 26
            opacity: 0.5
            anchors.centerIn: parent
            source: root.menuImageSource
            sourceSize.height: 28
            sourceSize.width: 28
            fillMode: Image.PreserveAspectFit
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true

            // Tooltip for the collapse button
            ToolTip.delay: Constants.defaultTooltipDelay
            ToolTip.timeout: Constants.defaultTooltipTimeout
            ToolTip.visible: mouseArea.containsMouse
            ToolTip.text: qsTr("Collapse Left Menu.")
        }
    }

    states: [
        State {
            name: "Mouse_Entered"
            when: mouseArea.containsMouse
            PropertyChanges {
                target: collapseIconImage
                opacity: 1.0
            }
            // PropertyChanges {
            //     target: bgCircle
            //     color: "#b65a1c"
            // }
        },
        State {
            name: "Mouse_Exited"
            when: !mouseArea.containsMouse
            PropertyChanges {
                target: collapseIconImage
                opacity: root.menuImageOpacityDefault
            }
            // PropertyChanges {
            //     target: collapse_menu_item
            //     color: Constants.barBackgroundColorLeftNav
            // }
        }
    ]
}
