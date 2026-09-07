
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
    height: 24
    width: tagBg.width

    property string text: "Some tag"
    property color color: "#632910"
    property color textColor: Constants.textColorChannelsHeroLabels
    property int radius: Math.ceil(height / 2)
    property int fontSize: Constants.textFontPixelSizeDefault
    property int padding: 20

    Rectangle {
        id: tagBg
        anchors.fill: parent
        radius: root.radius
        color: root.color
        width: tagLabel.implicitWidth + root.padding

        Text {
            id: tagLabel
            text: root.text
            anchors.centerIn: parent
            color: root.textColor
            font.pixelSize: root.fontSize
        }
    }
}
