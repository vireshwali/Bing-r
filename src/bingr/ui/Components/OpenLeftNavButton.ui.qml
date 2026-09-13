import QtQuick
import QtQuick.Controls
import ui

Item {
    id: root
    width: 45
    height: width

    // properties
    readonly property url openIconImageSource: Qt.resolvedUrl(
                                                   "../images/arrows-open.svg")
    readonly property double openIconImageOpacityDefault: 0.6

    readonly property double hoverBackgroundColor: Qt.lighter(
                                                       Constants.backgroundColor,
                                                       1.8)

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: bgRect
        anchors.fill: parent
        color: Constants.backgroundColor
        radius: width / 2
        border.width: 0

        Image {
            id: openIconImage
            width: 30
            height: 30
            anchors.centerIn: parent
            source: root.openIconImageSource
            cache: true
            mipmap: true
            asynchronous: true
            opacity: root.openIconImageOpacityDefault
            sourceSize.height: 30
            sourceSize.width: 30
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
            ToolTip.text: qsTr("Open Left Menu.")
        }
    }

    states: [
        State {
            name: "Mouse_Entered"
            when: mouseArea.containsMouse
            PropertyChanges {
                target: bgRect
                color: root.hoverBackgroundColor
            }
            PropertyChanges {
                target: openIconImage
                opacity: 1.0
            }
        },
        State {
            name: "Mouse_Exited"
            when: !mouseArea.containsMouse
            PropertyChanges {
                target: bgRect
                color: Constants.backgroundColor
            }
            PropertyChanges {
                target: openIconImage
                opacity: root.openIconImageOpacityDefault
            }
        }
    ]
}
