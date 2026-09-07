import QtQuick
import QtQuick.Studio.DesignEffects
import ui.Components

Item {
    id: root
    width: 210
    height: 800

    // EXPORT THE TARGET NAV BUTTONS FOR EXTERNAL BINDINGS
    property alias homeMenuButton: homeBtn
    property alias favouritesMenuButton: favouritesBtn
    //property alias playlistsMenuButton: playlistsBtn
    property alias channelsMenuButton: channelsBtn
    property alias settingsMenuButton: settingsBtn
    property alias collapseBtn: collapseBtn

    readonly property int columnItemsSpacing: 22
    readonly property int columnItemsLeftMargin: 24

    readonly property bool hovered: navHoverHandler.hovered

    Rectangle {
        id: navPanel
        color: Constants.barBackgroundColorLeftNav
        anchors.fill: parent

        HoverHandler {
            id: navHoverHandler
        }

        Rectangle {
            id: rectangle
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            z: 2
            height: 90
            color: "#b65a1c"

            Text {
                id: text1
                color: "#e6931f"
                text: qsTr("Bing-r")
                font.pixelSize: 48
                anchors.horizontalCenterOffset: 23
                anchors.verticalCenterOffset: -2
                anchors.centerIn: parent
                font.bold: true
                font.italic: true

                DesignEffect {
                    effects: [
                        DesignDropShadow {
                            color: "#ab000000"
                            offsetY: 5
                            offsetX: 1
                            blur: 6
                        }
                    ]
                }
            }
        }

        CollapseLeftNavButton {
            id: collapseBtn
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.topMargin: 8
            z: 4
        }

        // Column {
        //     id: topBtnsCol
        //     anchors.top: rectangle.bottom
        //     anchors.topMargin: 20
        //     anchors.left: parent.left
        //     anchors.leftMargin: root.columnItemsLeftMargin
        //     spacing: root.columnItemsSpacing

        //     LeftNavMenuButton {
        //         id: profileBtn
        //         menuText: qsTr("Profile")
        //         menuImageSource: Qt.resolvedUrl("images/user.svg")
        //         menuTooltipText: qsTr("View your User Profile.")
        //     }

        //     LeftNavMenuButton {
        //         id: searchBtn
        //         menuText: qsTr("Search")
        //         menuImageSource: Qt.resolvedUrl("images/search.svg")
        //         menuTooltipText: qsTr("Search your saved content.")
        //     }
        // }
        Column {
            id: midBtnsCol
            anchors.top: rectangle.bottom
            anchors.topMargin: 20
            anchors.left: parent.left
            anchors.leftMargin: root.columnItemsLeftMargin
            spacing: root.columnItemsSpacing

            // anchors.verticalCenter: parent.verticalCenter
            // anchors.left: parent.left
            // anchors.leftMargin: root.columnItemsLeftMargin
            // spacing: root.columnItemsSpacing
            LeftNavMenuButton {
                id: homeBtn
                menuText: qsTr("Home")
                menuImageSource: Qt.resolvedUrl("images/home.svg")
                menuTooltipText: qsTr("Go to Home.")
            }

            LeftNavMenuButton {
                id: favouritesBtn
                menuText: qsTr("Favourites")
                menuImageSource: Qt.resolvedUrl("images/heart.svg")
                menuTooltipText: qsTr("Go to Favourites.")
            }

            // LeftNavMenuButton {
            //     id: playlistsBtn
            //     menuText: qsTr("Playlists")
            //     menuImageSource: Qt.resolvedUrl("images/playlist.svg")
            //     menuTooltipText: qsTr("Go to your Platlists.")
            // }
            LeftNavMenuButton {
                id: channelsBtn
                menuText: qsTr("Channels")
                menuImageSource: Qt.resolvedUrl("images/television.svg")
                menuTooltipText: qsTr("View added IPTV channels.")
            }
        }

        Column {
            id: botBtnsCol
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 10
            anchors.left: parent.left
            anchors.leftMargin: root.columnItemsLeftMargin
            spacing: root.columnItemsSpacing

            LeftNavMenuButton {
                id: settingsBtn
                menuText: qsTr("Settings")
                menuImageSource: Qt.resolvedUrl("images/settings.svg")
                menuTooltipText: qsTr("Manage app Settings.")
            }

            LeftNavMenuButton {
                id: helpBtn
                menuText: qsTr("Help")
                menuImageSource: Qt.resolvedUrl("images/help-circle.svg")
                menuTooltipText: qsTr("Get Help & Support.")
            }
        }
    }
}
