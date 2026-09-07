import QtQuick
import QtQuick.Controls
import bingr.controllers

Item {
    id: root
    width: 1050
    height: 26

    property int imageWidth: 22
    property int imageHeight: 22
    property int fontSizePx: 13
    property string internetStatusTooltipText: "Connection is good"
    property string diskStatusTooltipText: "Disk size is good"
    property string ramStatusTooltipText: "Memory is good"

    Rectangle {
        id: statusBarBg
        color: Constants.barBackgroundColorStatusBar
        border.color: Constants.barBackgroundColorStatusBar
        anchors.fill: parent
        border.width: 0

        Row {
            id: leftRow
            height: parent.height
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 8
            spacing: 10

            Image {
                id: userIcon
                width: root.imageWidth
                height: root.imageHeight
                source: Qt.resolvedUrl("./images/user-logged-out.svg")
                smooth: true
                anchors.verticalCenter: parent.verticalCenter
                antialiasing: true
                fillMode: Image.PreserveAspectFit
                sourceSize.height: 28
                sourceSize.width: 28
            }

            Text {
                id: channelsLabel
                color: "#b7b7b7"
                anchors.verticalCenter: parent.verticalCenter
                font.letterSpacing: 0
                text: qsTr("Channels: 100000")
                font.pixelSize: root.fontSizePx
                renderType: Text.NativeRendering
                font.weight: Font.Normal
            }

            Text {
                id: favouritesLabel
                color: "#bebebe"
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Favourites: 123456")
                font.pixelSize: root.fontSizePx
            }

            Text {
                id: playlistsLabel
                color: "#bebebe"
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Playlists: 0")
                font.pixelSize: root.fontSizePx
            }
        }

        Row {
            id: rightRow
            height: parent.height
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 10
            spacing: 8

            Text {
                id: progressMsg
                color: "#b7b7b7"
                anchors.verticalCenter: parent.verticalCenter
                font.letterSpacing: 0.1
                text: qsTr("Idle.")
                font.pixelSize: root.fontSizePx
                renderType: Text.NativeRendering
                font.weight: Font.Normal
            }

            Rectangle {
                width: 1
                anchors.verticalCenter: parent.verticalCenter
                height: parent.height - 12
                color: "#929292"
                border.width: 0
            }

            Image {
                id: internetStatusImage
                width: root.imageWidth
                height: root.imageHeight
                source: "images/internet-off.svg"
                anchors.verticalCenter: parent.verticalCenter
                sourceSize.height: 28
                sourceSize.width: 28
                fillMode: Image.PreserveAspectFit

                MouseArea {
                    id: internetStatusImageMouseArea
                    anchors.fill: parent
                    hoverEnabled: true

                    // Tooltip for the menu item
                    ToolTip.delay: Constants.defaultTooltipDelay
                    ToolTip.timeout: Constants.defaultTooltipTimeout
                    ToolTip.visible: internetStatusImageMouseArea.containsMouse
                    ToolTip.text: root.internetStatusTooltipText
                }
            }

            Image {
                id: diskStatusImage
                width: root.imageWidth
                height: root.imageHeight
                source: "images/disk-green.svg"
                anchors.verticalCenter: parent.verticalCenter
                sourceSize.height: 28
                sourceSize.width: 28
                fillMode: Image.PreserveAspectFit

                MouseArea {
                    id: diskStatusImageMouseArea
                    anchors.fill: parent
                    hoverEnabled: true

                    // Tooltip for the menu item
                    ToolTip.delay: Constants.defaultTooltipDelay
                    ToolTip.timeout: Constants.defaultTooltipTimeout
                    ToolTip.visible: diskStatusImageMouseArea.containsMouse
                    ToolTip.text: root.diskStatusTooltipText
                }
            }

            Image {
                id: ramStatusImage
                width: root.imageWidth
                height: root.imageHeight
                source: "images/ram-red.svg"
                anchors.verticalCenter: parent.verticalCenter
                sourceSize.height: 28
                sourceSize.width: 28
                fillMode: Image.PreserveAspectFit

                MouseArea {
                    id: ramStatusImageMouseArea
                    anchors.fill: parent
                    hoverEnabled: true

                    // Tooltip for the menu item
                    ToolTip.delay: Constants.defaultTooltipDelay
                    ToolTip.timeout: Constants.defaultTooltipTimeout
                    ToolTip.visible: ramStatusImageMouseArea.containsMouse
                    ToolTip.text: root.ramStatusTooltipText
                }
            }

            Rectangle {
                width: 1
                anchors.verticalCenter: parent.verticalCenter
                height: parent.height - 12
                color: "#929292"
                border.width: 0
            }

            Text {
                id: appVersion
                color: "#888888"
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("v1.4.3.2")
                font.pixelSize: root.fontSizePx
            }
        }
    }

    Connections {
        target: StatusBarController

        function onProgressMsg(msg) {
            //console.log("Progress msg: ", msg)
            progressMsg.text = qsTr(msg)
        }

        function onInternetStatus(msg, msgType) {
            //console.log("onInternetStatus: ", msg, ", type: ", msgType)
            if (msgType === "success")
                internetStatusImage.source = Qt.resolvedUrl(
                            "images/internet-on.svg")
            else
                internetStatusImage.source = Qt.resolvedUrl(
                            "images/internet-off.svg")

            root.internetStatusTooltipText = qsTr(msg)
        }

        function onDiskStatus(msg, msgType) {
            //console.log("onDiskStatus: ", msg, ", type: ", msgType)
            if (msgType === "success")
                diskStatusImage.source = Qt.resolvedUrl("images/disk-green.svg")
            else if (msgType === "warning")
                diskStatusImage.source = Qt.resolvedUrl(
                            "images/disk-yellow.svg")
            else
                diskStatusImage.source = Qt.resolvedUrl("images/disk-red.svg")

            root.diskStatusTooltipText = qsTr(msg)
        }

        function onRamStatus(msg, msgType) {
            //console.log("onRamtatus: ", msg, ", type: ", msgType)
            if (msgType === "success")
                ramStatusImage.source = Qt.resolvedUrl("images/ram-green.svg")
            else if (msgType === "warning")
                ramStatusImage.source = Qt.resolvedUrl("images/ram-yellow.svg")
            else
                ramStatusImage.source = Qt.resolvedUrl("images/ram-red.svg")

            root.ramStatusTooltipText = qsTr(msg)
        }

        function onChannelsMsg(msg) {
            //console.log("onChannelsMsg: ", msg)
            channelsLabel.text = msg
        }

        function onFavouritesMsg(msg) {
            //console.log("onFavouritesMsg: ", msg)
            favouritesLabel.text = msg
        }

        function onPlaylistsMsg(msg) {
            //console.log("onPlaylistsMsg: ", msg)
            playlistsLabel.text = msg
        }
    }
}
