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
    property int minCardWidth: 240
    property int maxColumns: 8
    readonly property int columns: Math.min(
                                       maxColumns, Math.max(
                                           1, Math.floor(
                                               width / (minCardWidth + gridSpacing))))
    readonly property real gridSpacing: 12
    readonly property int sideMargin: 24
    readonly property int cacheBuffer: 200

    // ── Grid View ──
    GridView {
        id: channelsGridView
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        model: root.gridController.channelsViewModel
        cellWidth: Math.floor(width / root.columns)
        cellHeight: cellWidth + 46
        //cellHeight: 295
        cacheBuffer: root.cacheBuffer
        clip: true

        //reuseItems: true
        //focus: true
        //keyNavigationEnabled: true
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
            cardPadding: Math.round(root.gridSpacing / 2)

            // 1. Force smooth tracking of visual coordinate shifts during resize
            Behavior on x {
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.Linear
                }
            }
            Behavior on y {
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.Linear
                }
            }

            // 2. Smoothly scale item dimensions simultaneously
            Behavior on width {
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.Linear
                }
            }
            Behavior on height {
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.Linear
                }
            }
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

        // Connections {
        //     target: channelsGridView.Keys

        //     function onPressed(event) {
        //         console.log("event: " + event)
        //         if (event.key === Qt.Key_PageDown) {
        //             channelsGridView.contentY = Math.min(
        //                         channelsGridView.contentY + channelsGridView.height,
        //                         channelsGridView.contentHeight - channelsGridView.height)
        //             event.accepted = true
        //         } else if (event.key === Qt.Key_PageUp) {
        //             channelsGridView.contentY = Math.max(
        //                         channelsGridView.contentY - channelsGridView.height,
        //                         0)
        //             event.accepted = true
        //         }
        //     }
        // }
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
