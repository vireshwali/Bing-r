import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    height: 36
    width: 300

    // properties
    property url imageSource: Qt.resolvedUrl("../images/checks.svg")
    property bool hideImage: false
    property string placeholderText: qsTr("Sample Placeholder")
    property string text: ""
    property int shadowSpreadSize: 4
    property int shadowBlur: 4

    //Export the MouseArea so parent files can bind to it
    property alias buttonMouseArea: mouseArea
    property alias textInput: textInputField

    Rectangle {
        id: textInputRect
        anchors.fill: parent
        color: Constants.backgroundColor
        radius: 8
        border.width: 0

        DesignEffect {
            effects: [
                DesignDropShadow {
                    id: dropShadow
                    color: "#3f545454"
                    spread: root.shadowSpreadSize
                    blur: root.shadowBlur
                    offsetY: 1
                }
            ]
        }

        Row {
            id: separatorRow
            anchors.fill: parent
            spacing: 4

            TextField {
                id: textInputField
                width: parent.width - iconBtnRect.width - (2 * separatorRow.spacing)
                height: parent.height
                color: "#cacaca"
                font.pixelSize: 14
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.NoWrap
                placeholderText: root.placeholderText
                text: root.text
                padding: 6
            }

            Rectangle {
                id: iconBtnRect
                width: parent.height
                height: parent.height * 0.9
                anchors.verticalCenter: parent.verticalCenter
                color: Constants.backgroundColor

                Image {
                    id: iconBtnImage
                    width: 26
                    height: 26
                    anchors.centerIn: parent
                    source: root.imageSource
                    sourceSize.width: 28
                    sourceSize.height: 28
                    fillMode: Image.PreserveAspectFit
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true

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
