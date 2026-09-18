
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
import QtQuick.Studio.DesignEffects
import bingr.controllers

Item {
    id: root
    width: 800
    height: 800

    property alias addChannelsBtn1: addChannelsBtn1
    property alias addChannelsBtn2: addChannelsBtn2
    property alias homeController: homeController

    property string starterMsg: qsTr("Your channels library is empty. <br/>Inorder to start watching, use the add channels button to add your m3u playlist files or urls.")
    property int topMargin: 0
    property int topNavLeftMargin: 8
    property int topNavHeight: 55
    property bool channelsExist: true

    Component.onCompleted: {
        console.log("Home onCompleted called.")
    }

    Component.onDestruction: {
        console.log("Home onDestruction called.")
    }

    HomeController {
        id: homeController
    }

    Connections {
        target: homeController
        function onChannelsExistInApp(channelsExist) {
            root.channelsExist = channelsExist
        }
    }

    Rectangle {
        id: rectangle
        anchors.fill: parent
        color: Constants.backgroundColor

        Item {
            id: starterMsgItem
            anchors.centerIn: parent
            width: parent.width * 0.8
            visible: !root.channelsExist
            implicitHeight: starterMsgLabel.height + 40

            Text {
                id: starterMsgLabel
                width: parent.width
                text: root.starterMsg
                font.letterSpacing: 0.2
                anchors.centerIn: parent
                color: Constants.textColorSecondary
                font.pixelSize: 24
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignTop
                lineHeight: 1.4
                wrapMode: Text.WordWrap
                font.wordSpacing: 0
                font.bold: true
            }

            IconButtonWithText {
                id: addChannelsBtn1
                height: 48
                anchors.top: starterMsgLabel.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: 32
                btnShadowBlur: 8
                btnShadowSpread: 8
            }
        }

        BusyIndicator {
            id: lodingIndictor
            width: 110
            height: 110
            anchors.centerIn: parent
            running: homeController.loading
            visible: running
            z: 10
        }

        Item {
            id: homeContentSection
            anchors.fill: parent
            visible: root.channelsExist

            Item {
                id: topNav
                height: root.topNavHeight
                anchors.top: parent.top
                anchors.topMargin: root.topMargin
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: root.topNavLeftMargin

                Text {
                    text: qsTr("Home")
                    color: Constants.textColorScreenTitle
                    font.pixelSize: Constants.textFontPixelSizeScreenTitle
                    font.weight: Font.Bold
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                }

                IconButtonWithText {
                    id: addChannelsBtn2
                    height: 36
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    btnRadius: 14
                    btnImageSize: 26
                    btnTextSize: Constants.textFontPixelSizeDefault
                    z: 10 //keep it above the flickable
                    btnShadowBlur: 6
                    btnShadowSpread: 6
                }
            }

            Flickable {
                id: homeContentFlickable
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: topNav.height + 2
                contentHeight: homeContentColumn.childrenRect.height
                clip: true

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                Column {
                    id: homeContentColumn
                    width: parent.width
                    spacing: 20

                    HorizontalPager {
                        id: continueWatchingChannels
                        width: parent.width
                        height: 280
                        title: qsTr("Continue Watching")
                        channelModel: homeController.continueWatchingChannelsViewModel
                        visible: homeController.continueWatchingChannelsViewModel !== null
                        autoScrollInterval: 6900
                    }

                    HorizontalPager {
                        id: topCategory1
                        width: parent.width
                        height: 280
                        title: qsTr("Top in %1").arg(
                                   homeController.pagerViewModel1SectionTitle)
                        channelModel: homeController.pagerViewModel1
                        visible: homeController.pagerViewModel1 !== null
                        autoScrollInterval: 6000
                    }

                    HorizontalPager {
                        id: topCategory2
                        width: parent.width
                        height: 280
                        title: qsTr("Top in %1").arg(
                                   homeController.pagerViewModel2SectionTitle)
                        channelModel: homeController.pagerViewModel2
                        visible: homeController.pagerViewModel2 !== null
                        autoScrollInterval: 6300
                    }

                    HorizontalPager {
                        id: topCategory3
                        width: parent.width
                        height: 280
                        title: qsTr("Top in %1").arg(
                                   homeController.pagerViewModel3SectionTitle)
                        channelModel: homeController.pagerViewModel3
                        visible: homeController.pagerViewModel3 !== null
                        autoScrollInterval: 6500
                    }

                    HorizontalPager {
                        id: topCategory4
                        width: parent.width
                        height: 280
                        title: qsTr("Top in %1").arg(
                                   homeController.pagerViewModel4SectionTitle)
                        channelModel: homeController.pagerViewModel4
                        visible: homeController.pagerViewModel4 !== null
                        autoScrollInterval: 6700
                    }

                    HorizontalPager {
                        id: recentlyAddedChannels
                        width: parent.width
                        height: 280
                        title: qsTr("Recently Added")
                        channelModel: homeController.recentlyAddedChannelsViewModel
                        visible: homeController.recentlyAddedChannelsViewModel !== null
                        autoScrollInterval: 7100
                    }
                }
            }

            Connections {
                target: topCategory1
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }

            Connections {
                target: topCategory2
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }

            Connections {
                target: topCategory3
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }

            Connections {
                target: topCategory4
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }

            Connections {
                target: continueWatchingChannels
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }

            Connections {
                target: recentlyAddedChannels
                function onChannelPlayRequested(channelId) {
                    homeController.channelIdPlayRequested(channelId)
                }
            }
        }
    }
}
