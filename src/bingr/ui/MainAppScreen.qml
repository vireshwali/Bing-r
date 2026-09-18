import QtQuick
import QtQuick.Studio.DesignEffects
import QtQuick.Layouts
import ui.Screens
import ui.Components
import bingr.controllers

Item {
    id: root
    width: Constants.width
    height: Constants.height

    property bool leftNavOpened: false
    property bool showPlayer: false
    property int pendingChannelId: -1

    property bool leftNavHovered: leftNav.hovered
                                  || openLeftNavBtn.buttonMouseArea.containsMouse

    Timer {
        id: leftNavIdleTimer
        interval: 800
        repeat: false
        running: root.leftNavOpened && !root.leftNavHovered
        onTriggered: root.leftNavOpened = false
    }

    Rectangle {
        id: mainScreenRect
        border.width: 0
        anchors.fill: parent
        color: Constants.backgroundColor
        antialiasing: true

        Connections {
            target: channelsScreenLoader.item ? channelsScreenLoader.item.channelsController : null
            function onChannelIdToPlay(channelId) {
                console.log("onChannelIdToPlay " + channelId)
                root.pendingChannelId = channelId
                root.showPlayer = true
            }
        }

        Connections {
            target: homeScreenLoader.item ? homeScreenLoader.item.homeController : null
            function onChannelIdToPlay(channelId) {
                console.log("onChannelIdToPlay from home " + channelId)
                root.pendingChannelId = channelId
                root.showPlayer = true
            }
        }

        Connections {
            target: favouritesScreenLoader.item
                      ? favouritesScreenLoader.item.favoritesController
                      : null
            function onChannelIdToPlay(channelId) {
                root.pendingChannelId = channelId
                root.showPlayer = true
            }
        }

        // left nav open and clsoe button connections
        Connections {
            target: openLeftNavBtn.buttonMouseArea
            function onClicked() {
                root.leftNavOpened = true
            }
        }

        Connections {
            target: leftNav.collapseBtn.buttonMouseArea
            function onClicked() {
                root.leftNavOpened = false
            }
        }

        // Left nav Menu items click connections
        Connections {
            target: leftNav.homeMenuButton.buttonMouseArea
            function onClicked() {
                console.log("Home  Button clciked.")
                //unset other screen laoders
                channelsScreenLoader.sourceComponent = null
                favouritesScreenLoader.sourceComponent = null
                settingsScreenLoader.sourceComponent = null
                addChannelsScreenLoader.sourceComponent = null

                //set home screen
                var homeScreenComp = Qt.createComponent("ui.Screens", "Home")
                if (homeScreenComp.status === Component.Ready) {
                    homeScreenLoader.sourceComponent = homeScreenComp
                    homeScreenLoader.item.topNavLeftMargin = openLeftNavBtn.width + 10
                    // homeScreenLoader.item.topNavHeight = openLeftNavBtn.height
                    //         + openLeftNavBtn.anchors.topMargin + 8
                    mainStackContainer.currentIndex = 0
                } else {
                    console.error("Error loading homeScreenComp component:",
                                  homeScreenComp.errorString())
                }
            }
        }

        Connections {
            target: leftNav.favouritesMenuButton.buttonMouseArea
            function onClicked() {
                //unset other screen laoders
                homeScreenLoader.sourceComponent = null
                channelsScreenLoader.sourceComponent = null
                settingsScreenLoader.sourceComponent = null
                addChannelsScreenLoader.sourceComponent = null

                //set screen
                var favouritesScreenComp = Qt.createComponent("ui.Screens",
                                                              "Favourites")
                if (favouritesScreenComp.status === Component.Ready) {
                    favouritesScreenLoader.sourceComponent = favouritesScreenComp
                    favouritesScreenLoader.item.topNavLeftMargin
                            = openLeftNavBtn.width + openLeftNavBtn.anchors.leftMargin
                    mainStackContainer.currentIndex = 1
                } else {
                    console.error(
                                "Error loading favouritesScreenComp component:",
                                favouritesScreenComp.errorString())
                }
            }
        }

        // Connections {
        //     target: leftNav.playlistsMenuButton.buttonMouseArea
        //     function onClicked() {
        //         mainStackContainer.currentIndex = 2
        //     }
        // }
        Connections {
            target: leftNav.channelsMenuButton.buttonMouseArea
            function onClicked() {
                //unset other screen laoders
                homeScreenLoader.sourceComponent = null
                favouritesScreenLoader.sourceComponent = null
                settingsScreenLoader.sourceComponent = null
                addChannelsScreenLoader.sourceComponent = null

                //set screen
                var channelsScreenComp = Qt.createComponent("ui.Screens",
                                                            "Channels")
                if (channelsScreenComp.status === Component.Ready) {
                    channelsScreenLoader.sourceComponent = channelsScreenComp
                    channelsScreenLoader.item.topNavLeftMargin = openLeftNavBtn.width
                            + openLeftNavBtn.anchors.leftMargin
                    mainStackContainer.currentIndex = 2
                } else {
                    console.error(
                                "Error loading channelsScreenComp component:",
                                channelsScreenComp.errorString())
                }
            }
        }

        Connections {
            id: connections
            target: homeScreenLoader.item.addChannelsBtn1.buttonMouseArea
            function onClicked() {
                //unset other screen laoders
                homeScreenLoader.sourceComponent = null
                channelsScreenLoader.sourceComponent = null
                favouritesScreenLoader.sourceComponent = null
                settingsScreenLoader.sourceComponent = null

                //set screen
                addChannelsScreenLoader.sourceComponent = Qt.createComponent(
                            "ui.Screens", "AddChannels")
                mainStackContainer.currentIndex = 3
            }
        }

        Connections {
            target: homeScreenLoader.item.addChannelsBtn2.buttonMouseArea
            function onClicked() {
                //unset other screen laoders
                homeScreenLoader.sourceComponent = null
                channelsScreenLoader.sourceComponent = null
                favouritesScreenLoader.sourceComponent = null
                settingsScreenLoader.sourceComponent = null

                //set screen
                addChannelsScreenLoader.sourceComponent = Qt.createComponent(
                            "ui.Screens", "AddChannels")
                mainStackContainer.currentIndex = 3
            }
        }

        Connections {
            target: leftNav.settingsMenuButton.buttonMouseArea
            function onClicked() {
                //unset other screen laoders
                homeScreenLoader.sourceComponent = null
                channelsScreenLoader.sourceComponent = null
                favouritesScreenLoader.sourceComponent = null
                addChannelsScreenLoader.sourceComponent = null

                //set screen
                settingsScreenLoader.sourceComponent = Qt.createComponent(
                            "ui.Screens", "Settings")
                mainStackContainer.currentIndex = 4
            }
        }

        OpenLeftNavButton {
            id: openLeftNavBtn
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.topMargin: 5 // half of (screens.topnav height - OpenLeftNavButton.height)
            z: 4
        }

        LeftNav {
            id: leftNav
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: statusBar.top
            anchors.leftMargin: -230
            anchors.topMargin: 12
            anchors.bottomMargin: 12
            z: 6

            DesignEffect {
                effects: [
                    DesignDropShadow {
                        visible: true
                        color: '#c3505050'
                        offsetY: 2
                        showBehind: true
                        offsetX: 2
                        blur: 28
                        spread: 5
                    }
                ]
            }
        }

        StackLayout {
            id: mainStackContainer
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: statusBar.top
            anchors.bottomMargin: 10
            currentIndex: 0

            // All screens are loaded at startup.
            // Changing 'currentIndex' toggles visibility instantly.
            Loader {
                id: homeScreenLoader
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
                sourceComponent: Home {
                    topNavLeftMargin: openLeftNavBtn.width + 10
                    //topNavHeight: openLeftNavBtn.height + openLeftNavBtn.anchors.topMargin
                }
            }

            Loader {
                id: favouritesScreenLoader
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
            }

            // Playlists {
            //     id: playlistsScreen
            //     Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            //     Layout.fillHeight: true
            //     Layout.fillWidth: true
            //}
            Loader {
                id: channelsScreenLoader
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
                //topNavLeftMargin: openLeftNavBtn.width + openLeftNavBtn.anchors.leftMargin
            }

            // Channels {
            //     id: channelsScreen
            //     Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            //     Layout.fillHeight: true
            //     Layout.fillWidth: true
            //     topNavLeftMargin: openLeftNavBtn.width + openLeftNavBtn.anchors.leftMargin
            // }
            Loader {
                id: addChannelsScreenLoader
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
                sourceComponent: null
            }

            Loader {
                id: settingsScreenLoader
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
                sourceComponent: null
            }
        }

        // Player overlay (sibling to StackLayout, overlays everything)
        Loader {
            id: playerScreenLoader
            source: "./Screens/PlayerScreen.qml"
            active: root.showPlayer
            anchors.fill: parent
            z: 100

            Connections {
                target: playerScreenLoader
                function onLoaded() {
                    if (playerScreenLoader.item) {
                        console.log("onLoaded " + root.pendingChannelId)
                        playerScreenLoader.item.channelId = root.pendingChannelId
                    }
                }
            }

            Connections {
                target: playerScreenLoader.item
                function onClosed() {
                    root.showPlayer = false
                    root.pendingChannelId = -1
                }
            }
        }

        StatusBar {
            id: statusBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }
    }
    states: [
        State {
            name: "LeftNavOpened"
            when: root.leftNavOpened
            PropertyChanges {
                target: leftNav
                anchors.leftMargin: 18
                //restoreEntryValues: false
            }
        }
    ]
    transitions: [
        Transition {
            id: leftNavOpenedTransition
            ParallelAnimation {
                SequentialAnimation {
                    PauseAnimation {
                        duration: 0
                    }

                    PropertyAnimation {
                        id: propertyAnimation
                        target: leftNav
                        property: "anchors.leftMargin"
                        easing.bezierCurve: [0.215, 0.61, 0.355, 1, 1, 1]
                        duration: 1100
                    }
                }
            }
            to: "*"
            from: "*"
        }
    ]
}
