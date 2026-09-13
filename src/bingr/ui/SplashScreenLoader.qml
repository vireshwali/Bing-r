import QtQuick
import ui.Screens

Window {
    id: root
    objectName: "splashWindow" // _boot_app() finds this by name to close it
    width: 750
    height: 425
    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2
    visible: true

    title: qsTr("")

    //this color is for visual etsting
    //color: "#1c1c1c"
    color: "#00000000"

    // Frameless window flags to make it look like a real splash screen
    flags: Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    modality: Qt.ApplicationModal

    Loader {
        id: splashScreenLoader
        anchors.fill: parent
        sourceComponent: SplashScreen {}

        Component.onCompleted: {
            console.log("SplashScreen Loader onCompleted called")
        }

        Component.onDestruction: {
            console.log("SplashScreen Loader onDestruction called.")
        }
    }
}
