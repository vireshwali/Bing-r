

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui

Item {
    id: root
    width: 800
    height: 800

    Rectangle {
        anchors.fill: parent
        color: Constants.backgroundColor

        Column {
            anchors.centerIn: parent
            spacing: 20

            Text {
                font.pixelSize: 28
                font.bold: true
                color: "#2c3e50"
                text: "Playlists"
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: 100
                height: 100
                color: "#ceb918"
                radius: 50
                anchors.horizontalCenter: parent.horizontalCenter
            }

            TextField {
                placeholderText: "Type text here, switch away, then come back..."
                width: 320
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }
}
