
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import ui
import ui.Components

Item {
    id: root
    width: 800
    height: 300

    property string title: qsTr("Channels")
    property var channelModel: null
    property int autoScrollInterval: 5000
    property int cardWidth: 210
    property int cardHeight: 150
    property int cardSpacing: 12

    signal channelPlayRequested(int channelId)

    Rectangle {
        id: background
        anchors.fill: parent
        color: Constants.backgroundColor

        Item {
            id: headerSection
            height: (sectionTitle.height
                     > seeMoreBtn.height ? sectionTitle.height : seeMoreBtn.height) + 12
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.right: parent.right

            Text {
                id: sectionTitle
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 12
                text: root.title
                color: Constants.textColorSecondary
                font.pixelSize: Constants.textFontPixelSizeUpper2
                font.weight: Font.Bold
            }

            //defer to release 2
            IconButtonWithText {
                id: seeMoreBtn
                height: 32
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 14
                btnImageSize: 24
                btnText: qsTr("See More")
                btnTextSize: Constants.textFontPixelSizeLower2
                btnTooptipText: qsTr("Click to go to channels page")
                btnImageSource: Qt.resolvedUrl("../images/dots-three.svg")
                btnShadowBlur: 3
                btnShadowSpread: 3
                visible: false
            }
        }

        CarouselArrow {
            id: prevArrow
            width: 32
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 4
            z: 4
            direction: "left"
            arrowEnabled: pagerList.currentIndex > 0
        }

        CarouselArrow {
            id: nextArrow
            width: 32
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 4
            z: 4
            direction: "right"
            arrowEnabled: pagerList.currentIndex < pagerList.count - 1
        }

        ListView {
            id: pagerList
            anchors.top: headerSection.bottom
            anchors.bottom: parent.bottom
            anchors.left: prevArrow.right
            anchors.right: nextArrow.left
            anchors.topMargin: 10
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            orientation: ListView.Horizontal
            model: root.channelModel
            spacing: root.cardSpacing
            snapMode: ListView.SnapToItem
            highlightRangeMode: ListView.StrictlyEnforceRange
            preferredHighlightBegin: 0
            preferredHighlightEnd: root.cardWidth
            boundsBehavior: Flickable.StopAtBounds
            highlightMoveVelocity: 500
            cacheBuffer: root.cardWidth * 2
            reuseItems: true
            clip: true
            delegate: PagerCard {
                id: pagerCard
                height: pagerList.height
                channelId: model.channelId
                logoUrl: Qt.resolvedUrl(model.logoUrl)
                countryCode: model.countryCode
                displayName: model.displayName
                category: model.category

                Connections {
                    target: pagerCard
                    function onPlayRequested(channelId) {
                        root.channelPlayRequested(channelId)
                    }
                }
            }
        }
    }

    Timer {
        id: autoScrollTimer
        interval: root.autoScrollInterval
        repeat: true
        running: true
    }

    Connections {
        target: prevArrow.buttonMouseArea
        function onClicked() {
            pagerList.decrementCurrentIndex()
        }
    }

    Connections {
        target: nextArrow.buttonMouseArea
        function onClicked() {
            pagerList.incrementCurrentIndex()
        }
    }

    Connections {
        target: autoScrollTimer
        function onTriggered() {
            if (pagerList.currentIndex >= pagerList.count - 1)
                pagerList.currentIndex = 0
            else
                pagerList.incrementCurrentIndex()
        }
    }
}
