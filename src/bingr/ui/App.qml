import QtQuick

Window {
    id: root
    width: Constants.width
    height: Constants.height
    // x: (Screen.width - width) / 2
    // y: (Screen.height - height) / 2
    minimumWidth: Constants.minimumWidth
    minimumHeight: Constants.minimumHeight

    visible: true
    title: qsTr("Bingr Mvp 1")
    color: systemPalette.window

    SystemPalette {
        id: systemPalette
    }

    MainAppScreen {
        id: mainScreen
        anchors.fill: parent
    }
}
