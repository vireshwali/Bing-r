import QtQuick
import QtQuick.Controls
import ui
import ui.Components
import QtQuick.Studio.DesignEffects

Item {
    id: root
    width: 350
    height: 210

    property url dialogTitleImg: Qt.resolvedUrl("../images/globe.svg")
    property string dialogTitle: qsTr("Some Sample Title To show")
    property string dialogMsg: qsTr("Some long message to show to the user with details of what happened and why and some description to show tot he user so that they can undertsand hwat happened here. they can undertsand hwat happened here")
    property string dialogMsgToolTip: qsTr("Some long message to show to the user with details of what happened and why and some description to show tot he user so that they can undertsand hwat happened here. they can undertsand hwat happened here")

    signal closed

    property alias closeBtnMouseArea: closeBtn.buttonMouseArea

    Rectangle {
        id: dialog
        anchors.fill: parent
        color: Constants.barBackgroundColorLeftNav
        border {
            color: Constants.accent
            width: 0
        }

        DesignEffect {
            effects: [
                DesignDropShadow {
                    color: "#3f737373"
                    offsetY: 2
                    spread: 18
                    blur: 32
                }
            ]
        }

        Item {
            id: item1
            anchors.fill: parent
            anchors.margins: 16

            Image {
                id: titleImage
                width: 30
                height: 30
                source: root.dialogTitleImg
                sourceSize.height: 32
                sourceSize.width: 32
                cache: false
                fillMode: Image.PreserveAspectFit
            }

            Text {
                id: title
                anchors.left: titleImage.right
                anchors.right: parent.right
                anchors.verticalCenter: titleImage.verticalCenter
                anchors.leftMargin: 10
                anchors.rightMargin: 0
                text: root.dialogTitle
                elide: Text.ElideRight
                color: Constants.textColorScreenTitle
                font.pixelSize: Constants.textFontPixelSizeUpper1
            }

            Text {
                id: msg
                width: parent.width
                anchors.top: titleImage.bottom
                anchors.topMargin: 10
                text: root.dialogMsg
                elide: Text.ElideRight
                color: Constants.textColorPrimary
                font.pixelSize: Constants.textFontPixelSizeDefault
                wrapMode: Text.WordWrap
                fontSizeMode: Text.VerticalFit
                maximumLineCount: 6

                HoverHandler {
                    id: msgHoverHandler
                    enabled: root.visible
                }

                ToolTip {
                    visible: msgHoverHandler.hovered
                    delay: Constants.defaultTooltipDelay
                    timeout: Constants.defaultTooltipTimeout
                    text: root.dialogMsgToolTip
                }
            }

            IconButtonWithText {
                id: closeBtn
                anchors.bottom: parent.bottom
                anchors.rightMargin: 4
                anchors.right: parent.right
                btnText: qsTr("Close")
                btnImageSource: Qt.resolvedUrl("../images/cancle.svg")
                btnImageSize: 24
                height: 36
                btnRadius: 18

                Connections {
                    target: closeBtn.buttonMouseArea
                    function onClicked() {
                        root.closed()
                    }
                }
            }
        }
    }
}
