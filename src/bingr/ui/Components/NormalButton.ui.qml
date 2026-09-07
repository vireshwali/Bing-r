import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    height: 36

    //implicit width of button = image left margin + width of image + text left margin + text implicit width + 8 (text rigth margin)
    implicitWidth: btnText.anchors.leftMargin + btnText.implicitWidth + btnText.anchors.rightMargin

    // properties
    property string btnText: qsTr("Add Channels")
    property double btnTextFontSizePx: 12
    property int btnTextLeftRightMargins: 12
    property string btnTooltipText: qsTr("Click to add channels.")

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea

    Rectangle {
        id: btnRect
        anchors.fill: parent
        color: Constants.backgroundColor
        radius: 10
        border.width: 0

        DesignEffect {
            effects: [
                DesignDropShadow {
                    id: dropShadow
                    color: "#3f545454"
                    spread: 4
                    blur: 8
                    offsetY: 1
                }
            ]
        }

        Text {
            id: btnText
            color: "#e7e7e7"
            height: parent.height
            anchors.centerIn: parent
            anchors.leftMargin: root.btnTextLeftRightMargins
            anchors.rightMargin: root.btnTextLeftRightMargins
            text: root.btnText
            font.pixelSize: root.btnTextFontSizePx
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            scale: 1
            hoverEnabled: true

            Connections {
                target: mouseArea
                function onPressed() {
                    btnRect.scale = 0.98
                }
            }

            Connections {
                target: mouseArea
                function onReleased() {
                    btnRect.scale = 1.0
                }
            }
        }
    }
    states: [
        State {
            name: "Mouse_Entered"
            when: mouseArea.containsMouse
            PropertyChanges {
                target: btnRect
                color: dropShadow.color
            }
        },
        State {
            name: "Mouse_Exited"
            when: !mouseArea.containsMouse
            PropertyChanges {
                target: btnRect
                color: Constants.backgroundColor
            }
        }
    ]
}
