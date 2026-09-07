import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 200
    height: 200
    visible: root.isRunning
    z: 1000

    property int indicatorWidthAndHeight: 64
    property bool isRunning: true

    Rectangle {
        anchors.fill: parent
        color: "#80000000"
        border.width: 0
        visible: root.isRunning
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.isRunning
    }

    BusyIndicator {
        id: loadingIndictor
        width: root.indicatorWidthAndHeight
        height: root.indicatorWidthAndHeight
        anchors.centerIn: parent
        running: root.isRunning
        visible: root.isRunning
    }
}
