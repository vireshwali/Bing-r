
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
import "HelperUtils.js" as HelperUrits
import QtQuick.Timeline 1.0

Item {
    id: root
    width: 240
    height: width + 95

    //data properties
    property int indexCount: 1000000
    property url logoUrl: "https://i.imgur.com/qKLEGU7.png"
    property string countryCode: "CA"
    property string quality: "HD"
    property string resolution: "720i"
    property bool isLive: true
    property string displayName: "The Pet Collective aadasd asda "
    property string altNames: "Duna 2, Duna II Auton\u00f3miA, Auton\u00f3miA"
    property string category: "Family"
    property string additionalTags: qsTr("Geo Blocked, Not 24/7")
    property int feedCount: 5
    property bool isFavorite: true
    property string languages: "English, Portuguese, French, Danish, Pakistani, African, French, Hindu, Gujarati, punjabi, kashmiriCanadian"

    // Card body
    Rectangle {
        id: cardRect
        anchors.fill: parent
        anchors.margins: 10
        radius: 12
        color: Constants.backgroundChannelsGridCardBg
        antialiasing: true
        clip: true

        // ── Logo area (16:9) ──
        Rectangle {
            id: logoSection
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: parent.width * 9 / 16
            radius: 12
            clip: true
            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: "#444444"
                }

                GradientStop {
                    position: 0.60
                    color: "#7c8a95"
                }

                GradientStop {
                    position: 1
                    color: Constants.backgroundChannelsGridCardBg
                }

                orientation: Gradient.Vertical
            }

            Text {
                id: channelCount
                color: Constants.accent
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 8
                anchors.topMargin: 8
                text: root.indexCount
                font.pixelSize: 12
            }

            Image {
                id: logoImg
                anchors.fill: parent
                anchors.bottomMargin: 20
                anchors.margins: 14
                source: root.logoUrl
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                mipmap: true
                transformOrigin: Item.Center
            }

            // Quality data
            Rectangle {
                id: qualityDataRect
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 8
                anchors.bottomMargin: 2
                height: 20
                color: "transparent"
                visible: root.quality !== ""
                width: qualText.implicitWidth + resolutionText.implicitWidth + 28

                Text {
                    id: qualText
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.quality
                    font.letterSpacing: 0.2
                    color: root.quality === "4K" ? Constants.quality4K : root.quality === "8K" ? Constants.quality8K : root.quality === "FHD" ? Constants.qualityFHD : root.quality === "QHD" ? Constants.qualityQHD : root.quality === "HD" ? Constants.qualityHD : Constants.qualitySD
                    font.pixelSize: 12
                    font.weight: Font.Medium
                }

                Text {
                    id: resolutionText
                    anchors.left: qualText.right
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.resolution
                    font.letterSpacing: 0.2
                    color: root.quality === "4K" ? Constants.quality4K : root.quality === "8K" ? Constants.quality8K : root.quality === "FHD" ? Constants.qualityFHD : root.quality === "QHD" ? Constants.qualityQHD : root.quality === "HD" ? Constants.qualityHD : Constants.qualitySD
                    font.pixelSize: 12
                    font.weight: Font.Medium
                }

                Image {
                    id: isFavouritedImage
                    width: 16
                    height: 16
                    anchors.left: resolutionText.right
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    source: (root.isFavorite) ? Qt.resolvedUrl(
                                                    "../images/heart-filled.svg") : ""
                    sourceSize.width: 40
                    sourceSize.height: 40
                    fillMode: Image.PreserveAspectFit
                }
            }

            // Country flag
            Image {
                anchors.right: parent.right
                anchors.verticalCenter: qualityDataRect.verticalCenter
                anchors.rightMargin: 8
                width: 25
                height: 12.5
                source: root.countryCode !== "" ? "https://flagcdn.com/w40/"
                                                  + root.countryCode.toLowerCase(
                                                      ) + ".png" : ""
                sourceSize.width: 40
                sourceSize.height: 20
                fillMode: Image.PreserveAspectFit
            }

            // Live dot
            Rectangle {
                id: rectangle
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 7
                anchors.rightMargin: 7
                width: 10
                height: 10
                radius: 5
                color: Constants.liveGreen
                visible: root.isLive
            }
        }

        // ── Info section ──
        Column {
            anchors.top: logoSection.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 8
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 8

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 3

                Text {
                    width: parent.width
                    text: root.displayName
                    color: Constants.textColorPrimary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                Text {
                    width: parent.width
                    color: Constants.textColorMuted
                    text: "[" + qsTr(root.altNames) + "]"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    visible: root.altNames !== ""
                }
            }

            Row {
                spacing: 6

                Text {
                    text: root.category !== "" ? root.category : "Uncategorized"
                    color: Constants.textColorMuted
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: qsTr("\u002D")
                    color: Constants.textColorMuted
                    font.pixelSize: 11
                    verticalAlignment: Text.AlignVCenter
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: root.feedCount + " Feeds"
                    color: Constants.textColorMuted
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                id: tagsText
                width: parent.width
                text: qsTr(root.additionalTags)
                color: Constants.textColorMuted
                font.pixelSize: 12
                elide: Text.ElideRight
                visible: root.additionalTags !== ""
            }

            Row {
                width: parent.width
                spacing: 8
                visible: root.languages !== ""

                Image {
                    id: userSepakerImg
                    width: 20
                    height: 20
                    anchors.verticalCenter: parent.verticalCenter
                    source: "../images/user-sound.svg"
                    sourceSize.height: 40
                    sourceSize.width: 40
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    id: languagesText
                    width: parent.width - userSepakerImg.width - parent.spacing
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.languages
                    color: Constants.textColorMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 3
                }
            }
        }

        // ── Action row (reveal on hover) ──
        Row {
            id: cardActions
            opacity: 0.3
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.bottomMargin: 8
            //z: 2
            anchors.rightMargin: 10
            spacing: 8

            IconButton {
                id: gridPlayBtn
                height: 32
                btnImageSize: 22
                btnImageSource: "../images/play.svg"
                btnShadowBlur: 4
                btnShadowSpread: 2

                Connections {
                    target: gridPlayBtn.buttonMouseArea
                    function onClicked() {
                        console.log("fav clicked")
                    }
                }
            }

            IconButton {
                id: gridFavBtn
                height: 32
                btnImageSize: 22
                btnImageSource: (root.isFavorite) ? Qt.resolvedUrl(
                                                        "../images/heart-filled.svg") : Qt.resolvedUrl(
                                                        "../images/heart.svg")
                btnShadowBlur: 4
                btnShadowSpread: 2
            }

            IconButton {
                id: gridWebsiteBtn
                height: 32
                btnImageSize: 22
                btnImageSource: "../images/globe.svg"
                btnShadowBlur: 4
                btnShadowSpread: 2
            }
        }

        DesignEffect {
            id: cardRectDesignEffect
            visible: false
            effects: [
                DesignDropShadow {
                    color: "#737a7a7a"
                    blur: 8
                    offsetY: 1
                    spread: 8
                }
            ]
        }

        HoverHandler {
            id: cardRectHover
        }
    }

    states: [
        State {
            name: "Card_Hovered"
            when: cardRectHover.hovered
            PropertyChanges {
                target: cardRect
                z: 10
            }
            PropertyChanges {
                target: cardActions
                opacity: 1.0
            }
            PropertyChanges {
                target: cardRectDesignEffect
                visible: true
            }
        }
    ]
}
