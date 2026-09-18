
import QtQuick
import QtQuick.Controls
import ui
import ui.Components
import bingr.controllers

Item {
    id: root
    width: 900
    height: 700

    property var gridController: null

    // ── Grid Layout ──
    property int cardWidth: 240
    property int columns: 4
    readonly property real gridSpacing: 12
    readonly property int sideMargin: 24
    readonly property int cacheBuffer: 200

    // ── Grid View ──
    GridView {
        id: channelsGridView
        anchors.fill: parent
        model: root.gridController.channelsViewModel
        cellWidth: root.cardWidth + root.gridSpacing
        cellHeight: root.cardWidth + 48 + root.gridSpacing
        cacheBuffer: root.cacheBuffer
        clip: true

        //boundsBehavior: Flickable.StopAtBounds
        delegate: ChannelsGridCard {
            id: gridDelegate
            width: channelsGridView.cellWidth
            //minus 4 for a bit of padding at last row
            height: channelsGridView.cellHeight - 4

            indexCount: (index + 1)
            channelId: model.channelId
            logoUrl: Qt.resolvedUrl(model.logoUrl)
            countryCode: model.countryCode
            quality: model.quality
            resolution: model.resolution
            isLive: model.isLive
            displayName: model.displayName
            altNames: model.altNames
            category: model.category
            additionalTags: model.additionalTags
            feedCount: model.feedCount
            isFavorite: model.isFavorite
            languages: model.languages
            websiteUrl: model.websiteUrl

            gridController: root.gridController
        }

        // Attaches the scrollbar with adaptive visibility
        ScrollBar.vertical: ScrollBar {
            id: vScrollBar

            // Shows when moving, hides when stationary
            policy: ScrollBar.AsNeeded

            // contentItem: Rectangle {
            //     color: "transparent"
            // }
            // Keeps the scrollbar inside the right edge of the grid view
            parent: channelsGridView
        }

        Connections {
            target: root.gridController
            function onGridIsLoading(isLoading) {
                //console.log("Received in QML onGridIsLoading:")
                if (isLoading) {
                    lodingIndictor.running = true
                } else {
                    lodingIndictor.running = false
                }
            }
        }
    }

    // ── Initial loading overlay ────────────────────────────────────────
    BusyIndicator {
        id: lodingIndictor
        width: 110
        height: 110
        anchors.centerIn: parent
        running: true
        visible: running
    }
}
