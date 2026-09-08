import QtQuick
import QtQuick.Studio.DesignEffects
import QtQuick.Effects

import bingr.controllers

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

    SystemPalette {
        id: systemPalette
    }

    Rectangle {
        id: rectangle
        anchors.fill: parent
        anchors.margins: designEffect.spread + 2

        color: "#1e1e24" // Dark slate background
        radius: 80
        border.width: 0

        // CRITICAL FIX: Cuts off the child image corners to match the radius
        clip: true

        DesignEffect {
            effects: [
                DesignDropShadow {
                    id: designEffect
                    color: "#4a484848"
                    offsetY: 0
                    spread: 18
                    blur: 24
                }
            ]
        }

        Image {
            id: splashBgImg
            source: "images/splashscreen_bg.jpg"
            sourceSize.height: 400
            sourceSize.width: 700
            fillMode: Image.Stretch
            anchors.fill: parent
            visible: false
        }

        MultiEffect {
            source: splashBgImg
            anchors.fill: splashBgImg
            maskEnabled: true
            maskSource: mask
        }

        Item {
            id: mask
            width: splashBgImg.width
            height: splashBgImg.height
            layer.enabled: true
            visible: false

            Rectangle {
                width: splashBgImg.width
                height: splashBgImg.height
                radius: 80
                color: "black"
            }
        }

        Text {
            id: title
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: 50
            anchors.topMargin: 40
            color: "#cccccc"
            text: qsTr("Bing-r")
            font.letterSpacing: 1.5
            font.pixelSize: 101
            minimumPixelSize: 80
        }

        Text {
            id: subtitle
            anchors.right: title.right
            anchors.top: title.bottom
            anchors.topMargin: 38
            color: "#b1b1b1"
            text: qsTr("Work Hard, Binge Harder")
            font.letterSpacing: 1.5
            font.pixelSize: 22
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            lineHeight: 1.2
            wrapMode: Text.WordWrap
            font.wordSpacing: 1
            minimumPixelSize: 22
        }

        Text {
            id: subtitle2
            anchors.right: subtitle.right
            anchors.top: subtitle.bottom
            anchors.topMargin: 10
            color: "#b1b1b1"
            text: qsTr("Curate. Organize. Discover. Watch.")
            font.letterSpacing: 1.5
            font.pixelSize: 22
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            lineHeight: 1.2
            wrapMode: Text.WordWrap
            font.wordSpacing: 1
            minimumPixelSize: 22
        }

        Text {
            id: loadingProgressMsgs
            width: root.width / 1.7
            height: 16
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: 64
            anchors.bottomMargin: 12
            text: qsTr("Initializing…")
            font.pixelSize: 14
            font.styleName: "Medium"
            color: "#a0a0a0"

            Connections {
                target: SplashScreenController
                function onProgressMsg(msg) {
                    console.log("progress msg received: ", msg)
                    loadingProgressMsgs.text = qsTr(msg)
                }
            }
        }

        Text {
            id: appVersion
            color: "#a0a0a0"
            text: SplashScreenController.appVersionSlug
            anchors.right: title.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 8
            anchors.bottomMargin: 12
            font.pixelSize: 14
        }
    }
}
