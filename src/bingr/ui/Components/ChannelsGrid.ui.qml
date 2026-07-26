
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
import bingr.controllers 1.0

Item {
    id: root
    width: 900
    height: 700

    // ── Hero State ──
    property int heroIndex: 0
    property bool heroHovered: false
    property var channelsModel: null

    // ── Grid Layout ──
    property int cardWidth: 280
    property int columns: 4
    readonly property real gridSpacing: 10
    readonly property int sideMargin: 24

    ListModel {
        id: dummyChannelsModel

        // ── 1 ──
        ListElement {
            channelId: "ArenaSport1.ba"
            displayName: "Arena Sport 1"
            logoUrl: "https://i.imgur.com/RJrJGbW.png"
            countryCode: "BA"
            countryName: "Bosnia and Herzegovina"
            category: "Sports"
            quality: "4K"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "Arena Sport 1 Bosna i Hercegovina"
            additionalTags: ""
            isFavorite: false
            languages: "Serbian"
            websiteUrl: "https://www.tvarenasport.com/ba"
        }
        // ── 2 ──
        ListElement {
            channelId: "DummyTV.de"
            displayName: "Dummy TV Germany"
            logoUrl: "https://placehold.co/300x168/1a1a2e/ffffff?text=Dummy+TV"
            countryCode: "DE"
            countryName: "Germany"
            category: "News"
            quality: "HD"
            resolution: "720p"
            feedCount: 2
            feedsCount: 2
            isLive: true
            altNames: "Dummy Deutschland, Dummy TV DE"
            additionalTags: "Geo-blocked"
            isFavorite: true
            languages: "German, English, French"
            websiteUrl: ""
        }
        // ── 3 ──
        ListElement {
            channelId: "AXNAdria.us"
            displayName: "AXN Adria"
            logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/AXN_logo_%282015%29.svg/960px-AXN_logo_%282015%29.svg.png"
            countryCode: "US"
            countryName: "United States"
            category: "Movies"
            quality: "SD"
            resolution: "480i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: ""
            isFavorite: false
            languages: "English"
            websiteUrl: "http://www.axn.com/"
        }
        // ── 4 ──
        ListElement {
            channelId: "TestChannel.ca"
            displayName: "Test Channel Canada"
            logoUrl: "https://placehold.co/300x168/16213e/ffffff?text=Test+Channel"
            countryCode: "CA"
            countryName: "Canada"
            category: "Sports"
            quality: "4K"
            resolution: "1080i"
            feedCount: 3
            feedsCount: 3
            isLive: true
            altNames: "Test Channel CA, Test Sports"
            additionalTags: ""
            isFavorite: false
            languages: "English, French"
            websiteUrl: ""
        }
        // ── 5 ──
        ListElement {
            channelId: "BHRT.ba"
            displayName: "BHRT"
            logoUrl: "https://i.imgur.com/01bZ5rw.png"
            countryCode: "BA"
            countryName: "Bosnia and Herzegovina"
            category: "General"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: "Geo-blocked"
            isFavorite: true
            languages: "Bosnian"
            websiteUrl: ""
        }
        // ── 6 ──
        ListElement {
            channelId: "SampleTV.br"
            displayName: "Sample TV Brazil"
            logoUrl: "https://placehold.co/300x168/0f3460/ffffff?text=Sample+TV"
            countryCode: "BR"
            countryName: "Brazil"
            category: "Movies"
            quality: "SD"
            resolution: "480i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "Sample Television, Sample TV BR"
            additionalTags: "Not 24/7"
            isFavorite: false
            languages: "Portuguese, Spanish, English"
            websiteUrl: ""
        }
        // ── 7 ──
        ListElement {
            channelId: "Federalnatelevizija.ba"
            displayName: "Federalna televizija"
            logoUrl: "https://i.imgur.com/astdRrE.png"
            countryCode: "BA"
            countryName: "Bosnia and Herzegovina"
            category: "General"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "Federal television, Federalna TV, Federal TV, FTV, TV FBiH"
            additionalTags: ""
            isFavorite: false
            languages: "Bosnian"
            websiteUrl: "https://www.federalna.ba/"
        }
        // ── 8 ──
        ListElement {
            channelId: "FakeNews.uk"
            displayName: "Fake News UK"
            logoUrl: "https://placehold.co/300x168/533483/ffffff?text=Fake+News"
            countryCode: "GB"
            countryName: "United Kingdom"
            category: "News"
            quality: "HD"
            resolution: "1080i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "FNews, Fake News United Kingdom"
            additionalTags: "Geo-blocked, Premium"
            isFavorite: true
            languages: "English"
            websiteUrl: ""
        }
        // ── 9 ──
        ListElement {
            channelId: "MariaPlusVisionMedjugorje.ba"
            displayName: "Maria+Vision Medjugorje"
            logoUrl: "https://i.imgur.com/xUOspBx.png"
            countryCode: "BA"
            countryName: "Bosnia and Herzegovina"
            category: "Religious"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "María+Visión Medjugorje"
            additionalTags: ""
            isFavorite: false
            languages: "Spanish"
            websiteUrl: "https://www.mariavisionmedjugorje.com/"
        }
        // ── 10 ──
        ListElement {
            channelId: "MockSports.in"
            displayName: "Mock Sports India"
            logoUrl: "https://placehold.co/300x168/1b98b0/ffffff?text=Mock+Sports"
            countryCode: "IN"
            countryName: "India"
            category: "Sports"
            quality: "HD"
            resolution: "720p"
            feedCount: 4
            feedsCount: 4
            isLive: true
            altNames: "Mock Sp, Mock Sports IN, मॉक स्पोर्ट्स"
            additionalTags: ""
            isFavorite: false
            languages: "Hindi, English, Tamil"
            websiteUrl: ""
        }
        // ── 11 ──
        ListElement {
            channelId: "MezzoLive.fr"
            displayName: "Mezzo Live"
            logoUrl: "https://i.imgur.com/H9ytKPN.png"
            countryCode: "FR"
            countryName: "France"
            category: "Music"
            quality: "SD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "Mezzo Live HD"
            additionalTags: ""
            isFavorite: false
            languages: "English"
            websiteUrl: "https://www.mezzo.tv/"
        }
        // ── 12 ──
        ListElement {
            channelId: "DemoKids.jp"
            displayName: "Demo Kids Japan"
            logoUrl: "https://placehold.co/300x168/e94560/ffffff?text=Demo+Kids"
            countryCode: "JP"
            countryName: "Japan"
            category: "Kids"
            quality: "SD"
            resolution: "480i"
            feedCount: 2
            feedsCount: 2
            isLive: true
            altNames: "Demo Kids JP, デモキッズ"
            additionalTags: "Not 24/7"
            isFavorite: true
            languages: "Japanese, English"
            websiteUrl: ""
        }
        // ── 13 ──
        ListElement {
            channelId: "9Gem.au"
            displayName: "9Gem"
            logoUrl: "https://i.imgur.com/cwLzqaw.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "Entertainment"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: "Geo-blocked"
            isFavorite: false
            languages: "English"
            websiteUrl: "https://www.9now.com.au/"
        }
        // ── 14 ──
        ListElement {
            channelId: "TrialMusic.kr"
            displayName: "Trial Music Korea"
            logoUrl: "https://placehold.co/300x168/0a1936/ffffff?text=Trial+Music"
            countryCode: "KR"
            countryName: "South Korea"
            category: "Music"
            quality: "4K"
            resolution: "2160p"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "TrialMusic KR, 트라이얼 뮤직"
            additionalTags: "Premium"
            isFavorite: false
            languages: "Korean, English, Japanese"
            websiteUrl: ""
        }
        // ── 15 ──
        ListElement {
            channelId: "9Go.au"
            displayName: "9Go!"
            logoUrl: "https://i.imgur.com/RLijQI8.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "Entertainment"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: "Geo-blocked"
            isFavorite: false
            languages: "English"
            websiteUrl: "https://www.9now.com.au/"
        }
        // ── 16 ──
        ListElement {
            channelId: "SampleDoc.au"
            displayName: "Sample Doc Australia"
            logoUrl: "https://placehold.co/300x168/185a36/ffffff?text=Sample+Doc"
            countryCode: "AU"
            countryName: "Australia"
            category: "Documentary"
            quality: "HD"
            resolution: "1080i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: "Sample Documentary, Sample Doc AU"
            additionalTags: ""
            isFavorite: true
            languages: "English"
            websiteUrl: ""
        }
        // ── 17 ──
        ListElement {
            channelId: "EuronewsAlbania.al"
            displayName: "Euronews Albania"
            logoUrl: "https://i.imgur.com/Skf6vdi.png"
            countryCode: "AL"
            countryName: "Albania"
            category: "News"
            quality: "HD"
            resolution: "576i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: "YouTube"
            isFavorite: false
            languages: "Albanian"
            websiteUrl: "https://euronews.al/"
        }
        // ── 18 ──
        ListElement {
            channelId: "TestReligious.ph"
            displayName: "Test Religious PH"
            logoUrl: "https://placehold.co/300x168/6a1716/ffffff?text=Test+Religious"
            countryCode: "PH"
            countryName: "Philippines"
            category: "Religious"
            quality: "SD"
            resolution: "480i"
            feedCount: 2
            feedsCount: 2
            isLive: true
            altNames: "Test Rel, Test Religious Philippines"
            additionalTags: "Geo-blocked"
            isFavorite: false
            languages: "Tagalog, English, Spanish"
            websiteUrl: ""
        }
        // ── 19 ──
        ListElement {
            channelId: "ShalomWorld.us"
            displayName: "Shalom World"
            logoUrl: "https://i.imgur.com/wnNd3b8.png"
            countryCode: "US"
            countryName: "United States"
            category: "Religious"
            quality: "4K"
            resolution: "480i"
            feedCount: 1
            feedsCount: 1
            isLive: true
            altNames: ""
            additionalTags: "Geo-blocked"
            isFavorite: true
            languages: "English"
            websiteUrl: "https://shalomworld.org/"
        }
        // ── 20 ──
        ListElement {
            channelId: "DummyGeneral.mx"
            displayName: "Dummy General Mexico"
            logoUrl: "https://placehold.co/300x168/7a2d1a/ffffff?text=Dummy+General"
            countryCode: "MX"
            countryName: "Mexico"
            category: "General"
            quality: "HD"
            resolution: "720p"
            feedCount: 3
            feedsCount: 3
            isLive: true
            altNames: "Dummy Gen MX, Dummy General México"
            additionalTags: "Not 24/7"
            isFavorite: false
            languages: "Spanish, English"
            websiteUrl: ""
        }
    }

    // ── Grid View ──
    GridView {
        id: channelsGridView
        anchors.fill: parent
        model: root.channelsModel
        //model: dummyChannelsModel // fallback for design-time
        cellWidth: root.cardWidth + root.gridSpacing
        cellHeight: root.cardWidth + 75 + root.gridSpacing
        cacheBuffer: 200
        clip: true

        //boundsBehavior: Flickable.StopAtBounds
        delegate: ChannelsGridCard {
            id: gridDelegate
            width: channelsGridView.cellWidth
            //minus 4 for a bit of padding at last row
            height: channelsGridView.cellHeight - 4

            indexCount: (index + 1)
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
            target: ChannelsController
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

    // ── Error overlay ──────────────────────────────────────────────────
    // Rectangle {
    //     id: errorOverlay
    //     anchors.fill: parent
    //     visible: ChannelsController.error !== ""
    //     color: "#1a1a1a"

    //     Text {
    //         anchors.centerIn: parent
    //         text: "Error: " + ChannelsController.error
    //         color: Constants.textColorPrimary
    //         font.pixelSize: 16
    //         wrapMode: Text.WordWrap
    //         horizontalAlignment: Text.AlignHCenter
    //     }
    // }
}
