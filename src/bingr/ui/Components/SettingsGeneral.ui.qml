import QtQuick
import QtQuick.Controls

import ui
import ui.Components

Item {
    id: root
    width: 600
    height: settingColumn.height + title.height

    property alias hideNotWorkingChannelsWithOneFeedSwitchChecked: hideNotWorkingChannelsWithOneFeedSwitch.checked

    Rectangle {
        id: mainRect
        anchors.fill: parent
        color: Constants.backgroundColor

        Text {
            id: title
            text: qsTr("General")
            anchors.top: parent.top
            color: Constants.textColorPrimary
            font.pixelSize: Constants.textFontPixelSizeUpper2
            font.bold: true
        }

        Column {
            id: settingColumn
            anchors.top: title.bottom
            anchors.topMargin: 4
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            rightPadding: 12
            leftPadding: 28
            spacing: 8

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: hideNotWorkingChannelsWithOneFeedSwitch.height

                Text {
                    id: hideNotWorkingChannelsWithOneFeedLable
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Hide not working channels with only 1 feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                CustomSwitch {
                    id: hideNotWorkingChannelsWithOneFeedSwitch
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
