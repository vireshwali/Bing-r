

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui
import ui.Components
import bingr.controllers

Item {
    id: root

    width: 900
    height: 600

    property int volumePercent: 50

    property double controlRectDefaultOpacity: 0.3
    property double controlRectHoverOpacity: 1.0
    property double controlRectHideOpacity: 0.0
    property bool controlRectHovered: mouseArea.containsMouse
                                      || fullScreenBtn.buttonMouseArea.containsMouse
                                      || playBtn.buttonMouseArea.containsMouse
                                      || stopBtn.buttonMouseArea.containsMouse
                                      || streamsComboBox.hovered
                                      || subsComboBox.hovered
                                      || volumeSlider.hovered

    property bool controlRectIdle: false

    property int controlRectHideTimer: 4000

    property double controlRectWidthWithStreams: playerBgRect.width * 0.85
    property double controlRectWidthWithoutStreams: playerBgRect.width * 0.75
    property bool showStreamsComboBox: streamsComboBox.count > 1
    property double controlRectWidth: showStreamsComboBox ? controlRectWidthWithStreams : controlRectWidthWithoutStreams

    property var streamsViewModel: null
    property int currentStreamIndex: 0

    property var subtitlesViewModel: null
    property int currentSubtitleIndex: 0
    property bool showSubsComboBox: subsComboBox.count > 1

    signal subtitleActivated(int index)

    Connections {
        target: root
        function onCurrentSubtitleIndexChanged() {
            subsComboBox.currentIndex = root.currentSubtitleIndex
        }
    }

    property bool loading: true
    property bool isFullScreen: false

    property alias playBtn: playBtn
    property alias stopBtn: stopBtn
    property alias volumeSlider: volumeSlider
    property alias videoItem: videoItem
    property alias streamsComboBox: streamsComboBox
    property alias subsComboBox: subsComboBox
    property alias subsImage: subsImage
    property alias fullScreenBtn: fullScreenBtn

    Rectangle {
        id: playerBgRect
        anchors.fill: parent
        color: Constants.backgroundColor
        border.width: 0

        Item {
            id: playerMainRect
            anchors.fill: parent
            anchors.margins: 8
            clip: true

            MpvFramebufferObject {
                id: videoItem
                // @disable-check M16
                anchors.fill: parent
            }

            BusyIndicator {
                id: loadingIndicator
                width: 53
                height: 53
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 12
                running: root.loading
            }
        }
    }

    Rectangle {
        id: controlRect
        //width: root.controlRectWidth
        width: root.controlRectWidthWithStreams
        height: 75
        color: Constants.backgroundColorTableCell
        opacity: root.controlRectDefaultOpacity
        radius: 36
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 24

        Behavior on opacity {
            NumberAnimation {
                duration: 300
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
        }

        IconButton {
            id: fullScreenBtn
            height: 36
            anchors.left: parent.left
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            btnImageSize: 24
            btnShadowSpread: 4
            btnShadowBlur: 3
            btnImageSource: root.isFullScreen ? Qt.resolvedUrl(
                                                    "../images/arrows-in.svg") : Qt.resolvedUrl(
                                                    "../images/arrows-out.svg")
            btnTooptipText: root.isFullScreen ? qsTr("Exit Full Screen") : qsTr(
                                                    "Enter Full Screen")
        }

        IconButton {
            id: playBtn
            height: 36
            anchors.left: fullScreenBtn.right
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            btnImageSize: 24
            btnShadowSpread: 4
            btnShadowBlur: 3
            btnImageSource: Qt.resolvedUrl("../images/play.svg")
            btnTooptipText: qsTr("Play")
        }

        IconButton {
            id: stopBtn
            height: 36
            anchors.left: playBtn.right
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            btnImageSize: 24
            btnShadowSpread: 4
            btnShadowBlur: 3
            btnImageSource: Qt.resolvedUrl("../images/stop.svg")
            btnTooptipText: qsTr("Stop Playback")
        }

        Image {
            id: streamsImage
            width: 18
            height: 18
            source: Qt.resolvedUrl("../images/film-reel.svg")
            sourceSize.height: 18
            sourceSize.width: 18
            fillMode: Image.PreserveAspectFit
            anchors.left: stopBtn.right
            anchors.leftMargin: 26
            anchors.verticalCenter: parent.verticalCenter
            visible: root.showStreamsComboBox
        }

        ComboBox {
            id: streamsComboBox
            width: 110
            anchors.left: streamsImage.right
            anchors.leftMargin: 8
            anchors.verticalCenter: streamsImage.verticalCenter
            model: root.streamsViewModel
            textRole: "name"
            currentIndex: root.currentStreamIndex
            visible: root.showStreamsComboBox
            background: Rectangle {
                radius: 4
                color: Constants.backgroundColorComboBox
                border.color: Constants.borderColorComboBox
                border.width: 1
            }
        }

        Image {
            id: subsImage
            width: 18
            height: 18
            source: Qt.resolvedUrl("../images/closed-captioning.svg")
            sourceSize.height: 18
            sourceSize.width: 18
            fillMode: Image.PreserveAspectFit
            anchors.left: streamsComboBox.right
            anchors.leftMargin: 26
            anchors.verticalCenter: parent.verticalCenter
            visible: root.showSubsComboBox
        }

        ComboBox {
            id: subsComboBox
            width: 110
            anchors.left: subsImage.right
            anchors.leftMargin: 8
            anchors.verticalCenter: subsImage.verticalCenter
            model: root.subtitlesViewModel
            textRole: "name"
            visible: root.showSubsComboBox
            onActivated: (index) => root.subtitleActivated(index)
            background: Rectangle {
                radius: 4
                color: Constants.backgroundColorComboBox
                border.color: Constants.borderColorComboBox
                border.width: 1
            }
        }

        Image {
            id: volumeImage
            width: 18
            height: 18
            source: Qt.resolvedUrl("../images/speaker.svg")
            sourceSize.height: 18
            sourceSize.width: 18
            fillMode: Image.PreserveAspectFit
            anchors.right: volumeSlider.left
            anchors.rightMargin: 8
            anchors.verticalCenter: stopBtn.verticalCenter
        }

        Text {
            id: volumeValue
            color: Constants.textColorSecondary
            text: root.volumePercent + "%"
            font.pixelSize: 11
            anchors.bottom: volumeSlider.top
            anchors.bottomMargin: 4
            anchors.horizontalCenter: volumeSlider.horizontalCenter
        }

        Slider {
            id: volumeSlider
            width: 120
            from: 0
            to: 100
            value: 50
            stepSize: 1
            anchors.right: parent.right
            anchors.rightMargin: 20
            wheelEnabled: true
            anchors.verticalCenter: stopBtn.verticalCenter

            Connections {
                target: volumeSlider
                function onValueChanged() {
                    root.volumePercent = Math.round(volumeSlider.value)
                }
            }
        }

        Timer {
            id: controlRectIdleTimer
            interval: root.controlRectHideTimer
            repeat: false
            running: true
        }

        Connections {
            target: controlRectIdleTimer
            function onTriggered() {
                root.controlRectIdle = true
            }
        }

        Connections {
            target: root
            function onControlRectHoveredChanged() {
                controlRectIdleTimer.stop()
                root.controlRectIdle = false
                if (!root.controlRectHovered)
                    controlRectIdleTimer.restart()
            }
        }
    }
    states: [
        State {
            name: "ControlRect_Hovered"
            when: root.controlRectHovered
            PropertyChanges {
                target: controlRect
                opacity: root.controlRectHoverOpacity
            }
        },
        State {
            name: "ControlRect_Idle"
            when: root.controlRectIdle
            PropertyChanges {
                target: controlRect
                opacity: root.controlRectHideOpacity
            }
        }
    ]
}
