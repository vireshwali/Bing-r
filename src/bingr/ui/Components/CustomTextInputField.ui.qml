import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    height: 36
    width: 300

    // properties
    property int shadowSpreadSize: 4
    property int shadowBlur: 4
    property string placeholderText: qsTr("Sample Placeholder")

    //Export the MouseArea so parent files can bind to it
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

        TextField {
            id: textInputField
            width: parent.width
            height: parent.height
            color: "#cacaca"
            font.pixelSize: 14
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.NoWrap
            placeholderText: root.placeholderText
            padding: 6
        }
    }
}
