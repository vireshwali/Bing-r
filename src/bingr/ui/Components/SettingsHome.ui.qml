import QtQuick
import QtQuick.Controls

import ui
import ui.Components

Item {
    id: root
    width: 600
    height: settingColumn.height + title.height

    property alias continueWatchingChannelsSizeSpinBoxValue: continueWatchingChannelsSizeSpinBox.value
    property alias continueWatchingChannelsAutoScrollDelaySecondsSpinBoxValue: continueWatchingChannelsAutoScrollDelaySecondsSpinBox.value
    property alias category1ChannelsSizeSpinBoxValue: category1ChannelsSizeSpinBox.value
    property alias category1ChannelsAutoScrollDelaySecondsSpinBoxValue: category1ChannelsAutoScrollDelaySecondsSpinBox.value
    property alias category2ChannelsSizeSpinBoxValue: category2ChannelsSizeSpinBox.value
    property alias category2ChannelsAutoScrollDelaySecondsSpinBoxValue: category2ChannelsAutoScrollDelaySecondsSpinBox.value
    property alias category3ChannelsSizeSpinBoxValue: category3ChannelsSizeSpinBox.value
    property alias category3ChannelsAutoScrollDelaySecondsSpinBoxValue: category3ChannelsAutoScrollDelaySecondsSpinBox.value
    property alias category4ChannelsSizeSpinBoxValue: category4ChannelsSizeSpinBox.value
    property alias category4ChannelsAutoScrollDelaySecondsSpinBoxValue: category4ChannelsAutoScrollDelaySecondsSpinBox.value
    property alias recentlyAddedChannelsSizeSpinBoxValue: recentlyAddedChannelsSizeSpinBox.value
    property alias recentlyAddedChannelsAutoScrollDelaySecondsSpinBoxValue: recentlyAddedChannelsAutoScrollDelaySecondsSpinBox.value

    Rectangle {
        id: mainRect
        anchors.fill: parent
        color: Constants.backgroundColor

        Text {
            id: title
            text: qsTr("Home Screen")
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
            spacing: 10

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: continueWatchingChannelsSizeSpinBox.height

                Text {
                    id: continueWatchingChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum channels to show in 'Continue Watching' feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: continueWatchingChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: continueWatchingChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: continueWatchingChannelsAutoScrollDelaySecondsLable1
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("'Continue Watching' feed scroll delay in seconds:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: continueWatchingChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category1ChannelsSizeSpinBox.height

                Text {
                    id: category1ChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum channels to show in 1st 'Top In <Category>' feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category1ChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category1ChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: category1ChannelsAutoScrollDelaySeconds
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("1st 'Top In <Category>' feed scroll delay in seconds")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category1ChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category2ChannelsSizeSpinBox.height

                Text {
                    id: category2ChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum channels to show in 2nd 'Top In <Category>' feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category2ChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category2ChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: category2ChannelsAutoScrollDelaySeconds
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("2st 'Top In <Category>' feed scroll delay in seconds")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category2ChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category3ChannelsSizeSpinBox.height

                Text {
                    id: category3ChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum channels to show in 3rd 'Top In <Category>' feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category3ChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category3ChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: category3ChannelsAutoScrollDelaySeconds
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("3rd 'Top In <Category>' feed scroll delay in seconds")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category3ChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category4ChannelsSizeSpinBox.height

                Text {
                    id: category4ChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum channels to show in 4th 'Top In <Category>' feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category4ChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: category4ChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: category4ChannelsAutoScrollDelaySeconds
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("4th 'Top In <Category>' feed scroll delay in seconds")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: category4ChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: recentlyAddedChannelsSizeSpinBox.height

                Text {
                    id: recentlyAddedChannelsSize
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("Maximum 'Recently Added' channels to show in feed:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: recentlyAddedChannelsSizeSpinBox
                    width: 100
                    value: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    wheelEnabled: true
                    from: 8
                    to: 24
                }
            }

            Item {
                width: parent.width - parent.leftPadding - parent.rightPadding
                height: recentlyAddedChannelsAutoScrollDelaySecondsSpinBox.height

                Text {
                    id: recentlyAddedChannelsAutoScrollDelaySeconds
                    anchors.verticalCenter: parent.verticalCenter
                    text: qsTr("'Recently Added' channels feed scroll delay in seconds:")
                    color: Constants.textColorSecondary
                    font.pixelSize: Constants.textFontPixelSizeDefault
                }

                SpinBox {
                    id: recentlyAddedChannelsAutoScrollDelaySecondsSpinBox
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 100
                    value: 3
                    from: 3
                    to: 8
                    editable: true
                }
            }
        }
    }
}
