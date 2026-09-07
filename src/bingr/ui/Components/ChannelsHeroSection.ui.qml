
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
import QtQuick.Timeline 1.0
import bingr.controllers

Item {
    id: root
    width: 900
    height: 240

    // ── Hero State ──
    property int heroIndex: 0
    property bool heroHovered: false

    property var heroModel: null

    ListModel {
        id: dummyHeroModel

        ListElement {
            channelId: "AngelTV.in"
            displayName: "Angel TV"
            logoUrl: "https://i.imgur.com/qKLEGU7.png"
            countryCode: "IN"
            countryName: "India"
            category: "Religious"
            quality: "SD"
            resolution: "1080p"
            feedCount: 15
            isFavorite: true
            isLive: true
            websiteUrl: "https://www.angeltv.org"
            languages: "English, Tamil, Chinese"
            altNames: "asd, qweqwe, werwer, dfgdfg"
            additionalTags: "YouTube"
        }
        ListElement {
            channelId: "BloombergTV.us"
            displayName: "Bloomberg TV"
            logoUrl: "https://i.imgur.com/OuogLHx.png"
            countryCode: "US"
            countryName: "United States"
            category: "Business"
            quality: "4K"
            feedCount: 12
            isFavorite: false
            isLive: true
            websiteUrl: "https://www.bloomberg.com/live/us/btv"
            languages: "English"
        }
        ListElement {
            channelId: "ThePetCollective.us"
            displayName: "The Pet Collective"
            logoUrl: "https://i.imgur.com/yH7n2dF.png"
            countryCode: "US"
            countryName: "United States"
            category: "Family"
            quality: "SD"
            feedCount: 12
            isFavorite: false
            isLive: true
            websiteUrl: "https://www.thepetcollective.com/streaming/"
            languages: "English, Portuguese, French"
        }
        ListElement {
            channelId: "MovieSphere.us"
            displayName: "MovieSphere"
            logoUrl: "https://i.imgur.com/h1ejU90.png"
            countryCode: "US"
            countryName: "United States"
            category: "Movies"
            quality: "HD"
            feedCount: 9
            isFavorite: false
            isLive: true
            websiteUrl: "https://lionsgatechannels.com/movie-sphere"
            languages: "English, Portuguese, German"
        }
        ListElement {
            channelId: "ABCTV.au"
            displayName: "ABC TV"
            logoUrl: "https://i.imgur.com/DPVQSjM.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "General"
            quality: "HD"
            feedCount: 8
            isFavorite: false
            isLive: true
            websiteUrl: "https://iview.abc.net.au/channel/abc1"
            languages: "English"
        }
        ListElement {
            channelId: "FIFAPlus.uk"
            displayName: "FIFA+"
            logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/FIFA%2B_(2025).svg/960px-FIFA%2B_(2025).svg.png"
            countryCode: "UK"
            countryName: "United Kingdom"
            category: "Sports"
            quality: "HD"
            feedCount: 8
            isFavorite: false
            isLive: true
            websiteUrl: "https://www.plus.fifa.com/"
            languages: "English, French, German"
        }
        ListElement {
            channelId: "NatureTime.ca"
            displayName: "NatureTime"
            logoUrl: "https://i.imgur.com/72JmyjM.png"
            countryCode: "CA"
            countryName: "Canada"
            category: "Documentary"
            quality: "HD"
            feedCount: 7
            isFavorite: false
            isLive: true
            websiteUrl: "https://naturetimetv.com/"
            languages: "English, Portuguese, Spanish"
        }
        ListElement {
            channelId: "10Bold.au"
            displayName: "10 Bold"
            logoUrl: "https://i.imgur.com/2xglh33.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "Lifestyle"
            quality: "SD"
            feedCount: 6
            isFavorite: false
            isLive: true
            websiteUrl: "http://tenplay.com.au/"
            languages: "English"
        }
        ListElement {
            channelId: "9Gem.au"
            displayName: "9Gem"
            logoUrl: "https://i.imgur.com/cwLzqaw.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "Entertainment"
            quality: "SD"
            feedCount: 6
            isFavorite: false
            isLive: true
            websiteUrl: "https://www.9now.com.au/"
            languages: "English"
        }
        ListElement {
            channelId: "9Go.au"
            displayName: "9Go!"
            logoUrl: "https://i.imgur.com/RLijQI8.png"
            countryCode: "AU"
            countryName: "Australia"
            category: "Entertainment"
            quality: "SD"
            feedCount: 6
            isFavorite: false
            isLive: true
            websiteUrl: "https://www.9now.com.au/"
            languages: "English"
        }
    }

    Rectangle {
        id: heroSection
        anchors.fill: parent
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: "#333333"
            }
            GradientStop {
                position: 0.4
                color: "#222222"
            }
            GradientStop {
                position: 1.0
                color: Constants.backgroundColor
            }
        }

        // Nav arrows
        CarouselArrow {
            id: prevArrowBtn
            width: 32
            height: parent.height * 0.5
            direction: "left"
            arrowEnabled: root.heroIndex > 0
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter

            Connections {
                target: prevArrowBtn.buttonMouseArea
                function onClicked() {
                    root.heroIndex = Math.max(0, root.heroIndex - 1)
                }
            }
        }

        CarouselArrow {
            id: nextArrowBtn
            width: 32
            height: parent.height * 0.5
            direction: "right"
            arrowEnabled: root.heroIndex < 9
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter

            Connections {
                target: nextArrowBtn.buttonMouseArea
                function onClicked() {
                    root.heroIndex = Math.min(9, root.heroIndex + 1)
                }
            }
        }

        // START - Carousel dots
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 10
            spacing: 8

            Repeater {
                model: root.heroModel

                //model: dummyHeroModel
                delegate: Rectangle {
                    id: dotRect
                    height: 8
                    radius: 4
                    width: index === root.heroIndex ? 32 : 10
                    color: index === root.heroIndex ? Constants.accent : (dotRect.hovered ? "#777777" : "#525252")

                    property bool hovered: false

                    Behavior on width {
                        SpringAnimation {
                            spring: 2
                            damping: 0.8
                        }
                    }

                    MouseArea {
                        id: dotArea
                        anchors.fill: parent
                        hoverEnabled: true

                        Connections {
                            target: dotArea
                            function onClicked() {
                                root.heroIndex = index
                            }
                            function onEntered() {
                                if (index !== root.heroIndex)
                                    dotRect.hovered = true
                            }
                            function onExited() {
                                if (index !== root.heroIndex)
                                    dotRect.hovered = false
                            }
                        }
                    }
                }
            }
        } // END - Carousel dots

        // Hero content
        Repeater {
            id: heroContent
            model: root.heroModel

            //model: dummyHeroModel
            delegate: Item {
                width: heroSection.width
                height: heroSection.height
                anchors.left: prevArrowBtn.right
                anchors.right: nextArrowBtn.left
                visible: index === root.heroIndex

                // Watermark logo background
                Image {
                    anchors.fill: parent
                    source: model.logoUrl
                    sourceSize {
                        width: 900
                        height: 240
                    }
                    fillMode: Image.PreserveAspectCrop
                    opacity: 0.08
                    asynchronous: true
                    cache: false
                }

                // START - Main hero row
                Row {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 30
                    anchors.verticalCenter: parent.verticalCenter

                    // Logo
                    Rectangle {
                        id: heroLogoBox
                        width: parent.width * 0.26
                        height: parent.height * 0.85
                        radius: 0
                        color: Constants.backgroundColorHeroLogoPlaceholder
                        clip: true
                        anchors.verticalCenter: parent.verticalCenter
                        topRightRadius: 38
                        bottomLeftRadius: 38
                        bottomRightRadius: 0
                        topLeftRadius: 0

                        Image {
                            anchors.fill: parent
                            anchors.margins: 16
                            verticalAlignment: Image.AlignVCenter
                            source: model.logoUrl
                            sourceSize {
                                width: 200
                                height: 180
                            }
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            // mipmap: true
                        }

                        // Live dot
                        // Rectangle {
                        //     anchors.top: parent.top
                        //     anchors.right: parent.right
                        //     anchors.topMargin: 8
                        //     anchors.rightMargin: 8
                        //     width: 16
                        //     height: 16
                        //     radius: 8
                        //     color: Constants.liveGreen
                        //     visible: model.isLive
                        // }
                    }

                    // Details
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 14

                        Row {
                            spacing: 16

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: model.displayName
                                color: Constants.textColorChannelsHeroLabels
                                font.pixelSize: Constants.textFontPixelSizeHeroChannelName
                                font.weight: Font.Bold
                                elide: Text.ElideRight
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: qsTr("[" + model.altNames + "]")
                                color: Constants.textColorChannelsHeroLabels
                                font.pixelSize: Constants.textFontPixelSizeHeroChannelAltName
                                elide: Text.ElideRight
                                visible: model.altNames !== ""
                            }
                        }

                        Row {
                            spacing: 10

                            TagText {
                                text: model.category
                                color: "#632910"
                            }

                            TagText {
                                text: qsTr(model.quality + ", " + model.resolution)
                                color: "#104263"
                            }

                            TagText {
                                text: qsTr(model.feedCount + " Feeds")
                                color: "#635310"
                            }

                            TagText {
                                text: model.languages
                                color: "#621063"
                            }

                            TagText {
                                text: model.additionalTags
                                color: "#106313"
                                visible: model.additionalTags !== ""
                            }
                        }

                        // Row {
                        //     spacing: 10

                        //     TagText {
                        //         text: model.languages
                        //         color: "#621063"
                        //     }

                        //     TagText {
                        //         text: model.additionalTags
                        //         color: "#106313"
                        //         visible: model.additionalTags !== ""
                        //     }
                        // }

                        // START - Second Row
                        Row {
                            spacing: 18

                            IconButtonWithText {
                                id: watchNowBtn
                                height: 40
                                btnRadius: 20
                                btnImageSize: 26
                                btnImageSource: "../images/play.svg"
                                btnText: "Watch Now"

                                Connections {
                                    target: watchNowBtn.buttonMouseArea
                                    function onClicked() {
                                        ChannelsController.channelIdPlayRequested(
                                                    model.channelId)
                                    }
                                }
                            }

                            // IconButton {
                            //     id: favouritesBtn
                            //     height: 40
                            //     btnImageSource: "../images/heart.svg"
                            //     btnImageSize: 26
                            //     btnTooptipText: qsTr("Click to add channel to favourites")

                            //     Connections {
                            //         target: favouritesBtn.buttonMouseArea
                            //         function onClicked() {
                            //             console.log("fav clicked")
                            //         }
                            //     }
                            // }
                            IconButton {
                                id: websiteLinkBtn
                                height: 40
                                btnImageSource: "../images/globe.svg"
                                btnImageSize: 26
                                btnTooptipText: qsTr("Go to provider's website")
                                visible: model.websiteUrl !== ""

                                Connections {
                                    target: websiteLinkBtn.buttonMouseArea
                                    function onClicked() {
                                        if (model.websiteUrl !== "")
                                            Qt.openUrlExternally(
                                                        model.websiteUrl)
                                    }
                                }
                            }
                        } // END - Second Row
                    }
                } // END - Main hero row
            }
        }

        // Auto-scroll timer
        Timer {
            id: heroTimer
            interval: 5000
            repeat: true
            running: true
        }

        Connections {
            target: heroTimer
            function onTriggered() {
                root.heroIndex = (root.heroIndex + 1) % 10
            }
        }
    }
}
