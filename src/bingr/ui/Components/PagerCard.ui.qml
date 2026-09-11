import ".."
import QtQuick
import QtQuick.Studio.DesignEffects

Item {
    id: root
    width: 240
    height: 260

    property int cardRectDesignEffectSpread: 6

    signal playRequested(int channelId)

    //data props
    property int channelId: -1
    property url placeholderLogoUrl: "../images/television-big.svg"
    property url logoUrl: "https://i.imgur.com/qKLEGU7.png"
    property string countryCode: "CA"
    property string displayName: "The Pet Collective aadasd asda"
    property string category: "Family, General"

    Rectangle {
        anchors.fill: parent
        color: Constants.backgroundChannelsGridCardBg
    }

    Rectangle {
        id: cardRect
        anchors.fill: parent
        anchors.margins: 8
        radius: 12
        color: Constants.backgroundChannelsGridCardBg

        Rectangle {
            id: cardLogo
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 4
            height: parent.height * 0.55
            gradient: Gradient {
                GradientStop {
                    position: 0.05
                    color: Constants.backgroundChannelsGridCardBg
                }

                GradientStop {
                    position: 0.4
                    color: "#2a2a2a"
                }

                GradientStop {
                    position: 0.6
                    color: "#2a2a2a"
                }

                GradientStop {
                    position: 0.95
                    color: Constants.backgroundChannelsGridCardBg
                }

                orientation: Gradient.Vertical
            }

            Image {
                id: logoPlaceholder
                anchors.fill: parent
                anchors.margins: 22
                height: parent.height * 0.55
                source: root.placeholderLogoUrl
                sourceSize.width: parent.width
                sourceSize.height: parent.height
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                mipmap: true
                transformOrigin: Item.Center
                visible: logoImage.status !== Image.Ready
            }

            Image {
                id: logoImage
                anchors.fill: parent
                anchors.margins: 10
                height: parent.height * 0.55
                source: root.logoUrl
                z: 2
                sourceSize.width: parent.width
                sourceSize.height: parent.height
                cache: false
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                mipmap: true
                transformOrigin: Item.Center
                visible: status === Image.Ready
            }
        }
        Image {
            id: countryFlag
            width: 25
            height: 12.5
            anchors.bottom: cardLogo.bottom
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.bottomMargin: 4

            source: root.countryCode !== "" ? "https://flagcdn.com/w40/"
                                              + root.countryCode.toLowerCase(
                                                  ) + ".png" : ""
            asynchronous: true
            z: 8
            sourceSize.width: 40
            sourceSize.height: 20
            fillMode: Image.PreserveAspectFit
        }

        Column {
            id: cardDetailsColumn
            anchors.top: cardLogo.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6
            spacing: 8

            Text {
                width: parent.width
                text: root.displayName
                color: Constants.textColorPrimary
                font.pixelSize: Constants.textFontPixelSizeLower2
                font.weight: Font.Medium
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Text {
                width: parent.width
                text: root.category
                color: Constants.textColorMuted
                font.pixelSize: Constants.textFontPixelSizeLower3
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }

        IconButtonWithText {
            id: playBtn
            height: 36
            anchors.bottom: parent.bottom
            anchors.rightMargin: 10
            anchors.bottomMargin: 12
            anchors.right: parent.right
            btnImageSource: Qt.resolvedUrl("../images/play.svg")
            btnImageSize: 24
            btnText: qsTr("Watch now")
            btnTooptipText: qsTr("Click to play")

            Connections {
                target: playBtn.buttonMouseArea
                function onClicked() {
                    root.playRequested(root.channelId)
                }
            }
        }

        DesignEffect {
            id: cardRectDesignEffect
            effects: [
                DesignDropShadow {
                    color: "#737a7a7a"
                    blur: 6
                    offsetY: 1
                    spread: 4
                }
            ]
        }
    }
}
