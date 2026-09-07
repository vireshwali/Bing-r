
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ui
import ui.Components
import bingr.controllers

Item {
    id: root
    width: 1000
    height: 700
    property double mainBodyWidthPercent: 0.53

    SettingsController {
        id: settingsController
    }

    // Restart-required banner (controlled from controller signal)
    Rectangle {
        id: restartBanner
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        z: 10
        height: restartBanner.visible ? 44 : 0
        //visible: true
        visible: settingsController.restartRequired
        color: "#3d2f14"
        border.width: 1
        border.color: Constants.accent

        Text {
            anchors.centerIn: parent
            text: qsTr("Some changes require an application restart to take effect.")
            color: Constants.textColorPrimary
            font.pixelSize: Constants.textFontPixelSizeUpper1
        }
    }

    CustomBusyIndicator {
        id: lodingIndictor
        anchors.fill: parent
        indicatorWidthAndHeight: 80
        isRunning: settingsController.loading
    }

    Rectangle {
        id: mainRect
        anchors.fill: parent
        color: Constants.backgroundColor

        Item {
            id: mainBodyItem
            width: parent.width * root.mainBodyWidthPercent
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: footerBar.top
            anchors.bottomMargin: 8

            Text {
                id: screenTitle
                text: qsTr("Settings")
                anchors.top: parent.top
                anchors.topMargin: 20
                anchors.horizontalCenter: parent.horizontalCenter
                color: Constants.textColorScreenTitle
                font.pixelSize: 22
                font.bold: true
            }

            Flickable {
                id: settingsAreaFlickable
                width: parent.width
                anchors.top: screenTitle.bottom
                anchors.topMargin: 10
                anchors.bottom: parent.bottom
                contentHeight: contentColumn.height
                clip: true

                Column {
                    id: contentColumn
                    width: parent.width
                    spacing: 16

                    SettingsGeneral {
                        id: settingsGeneral
                        width: parent.width
                    }

                    SeparatorRect {
                        id: separatorRect1
                        height: 1
                        width: parent.width
                    }

                    SettingsHome {
                        id: settingsHome
                        width: parent.width
                    }
                }

                //----Scrollbar----
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
            }
        }

        // ── Footer bar ──────────────────────────────────────────
        Rectangle {
            id: footerBar
            height: 52
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            color: Constants.backgroundColor

            IconButtonWithText {
                id: resetBtn
                anchors.right: parent.right
                anchors.rightMargin: 28
                anchors.verticalCenter: parent.verticalCenter
                btnImageSource: Qt.resolvedUrl("../images/reset.svg")
                btnText: qsTr("Reset")
                btnImageSize: 28
            }

            IconButtonWithText {
                id: cancleBtn
                anchors.right: resetBtn.left
                anchors.rightMargin: 28
                anchors.verticalCenter: resetBtn.verticalCenter
                btnImageSource: Qt.resolvedUrl("../images/cancle.svg")
                btnText: qsTr("Cancle")
                btnImageSize: 28
            }

            IconButtonWithText {
                id: saveBtn
                anchors.right: cancleBtn.left
                anchors.rightMargin: 28
                anchors.verticalCenter: resetBtn.verticalCenter
                btnImageSource: Qt.resolvedUrl("../images/save.svg")
                btnText: qsTr("Save")
                btnImageSize: 28
            }
        }
    }

    // Confirmation dialog for "Reset to Defaults"
    // ConfirmDialog {
    //     id: confirmDialog
    //     parent: root
    //     anchors.centerIn: parent
    //     dialogTitle: qsTr("Reset all settings?")
    //     dialogMessage: qsTr("This will restore every setting to its default value and discard all unsaved changes. Continue?")
    //     okText: qsTr("Reset")
    //     destructive: true
    // }
    Component.onCompleted: {
        console.log("Settings onCompleted called")
        settingsController.getAllSettings()
    }

    Component.onDestruction: {
        console.log("Settings onDestruction called.")
    }

    Connections {
        target: settingsController
        function onSettingsCacheChanged() {
            //confirmDialog.open()
            console.log("onSettingsCacheChanged called")
            var settingsCache = settingsController.settingsCache
            console.log("Settings Dictionary:",
                        JSON.stringify(settingsCache, null, 2))

            // set the values for general
            settingsGeneral.hideNotWorkingChannelsWithOneFeedSwitchChecked
                    = settingsCache.hideNotWorkingChannelsWithOneFeed

            //set values for home settings
            settingsHome.continueWatchingChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenContinueWatchingChannelsSize
            settingsHome.continueWatchingChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenContinueWatchingChannelsAutoScrollDelaySeconds
            settingsHome.category1ChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenCategory1ChannelsSize
            settingsHome.category1ChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenCategory1ChannelsAutoScrollDelaySeconds
            settingsHome.category2ChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenCategory2ChannelsSize
            settingsHome.category2ChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenCategory2ChannelsAutoScrollDelaySeconds
            settingsHome.category3ChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenCategory3ChannelsSize
            settingsHome.category3ChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenCategory3ChannelsAutoScrollDelaySeconds
            settingsHome.category4ChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenCategory4ChannelsSize
            settingsHome.category4ChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenCategory4ChannelsAutoScrollDelaySeconds
            settingsHome.recentlyAddedChannelsSizeSpinBoxValue
                    = settingsCache.homeScreenRecentlyAddedChannelsSize
            settingsHome.recentlyAddedChannelsAutoScrollDelaySecondsSpinBoxValue
                    = settingsCache.homeScreenRecentlyAddedChannelsAutoScrollDelaySeconds
        }

        function onLoadingChanged() {
            console.log("onLoadingChanged called")
            console.log(settingsController.loading)
        }

        function onSaveCompleted() {
            console.log("Settings saved successfully.")
        }
    }

    Connections {
        target: saveBtn.buttonMouseArea
        function onClicked() {
            console.log("Settings save called.")
            var settingsDataPayload = {
                "hideNotWorkingChannelsWithOneFeed": settingsGeneral.hideNotWorkingChannelsWithOneFeedSwitchChecked,
                "homeScreenContinueWatchingChannelsSize": settingsHome.continueWatchingChannelsSizeSpinBoxValue,
                "homeScreenContinueWatchingChannelsAutoScrollDelaySeconds": settingsHome.continueWatchingChannelsAutoScrollDelaySecondsSpinBoxValue,
                "homeScreenCategory1ChannelsSize": settingsHome.category1ChannelsSizeSpinBoxValue,
                "homeScreenCategory1ChannelsAutoScrollDelaySeconds": settingsHome.category1ChannelsAutoScrollDelaySecondsSpinBoxValue,
                "homeScreenCategory2ChannelsSize": settingsHome.category2ChannelsSizeSpinBoxValue,
                "homeScreenCategory2ChannelsAutoScrollDelaySeconds": settingsHome.category2ChannelsAutoScrollDelaySecondsSpinBoxValue,
                "homeScreenCategory3ChannelsSize": settingsHome.category3ChannelsSizeSpinBoxValue,
                "homeScreenCategory3ChannelsAutoScrollDelaySeconds": settingsHome.category3ChannelsAutoScrollDelaySecondsSpinBoxValue,
                "homeScreenCategory4ChannelsSize": settingsHome.category4ChannelsSizeSpinBoxValue,
                "homeScreenCategory4ChannelsAutoScrollDelaySeconds": settingsHome.category4ChannelsAutoScrollDelaySecondsSpinBoxValue,
                "homeScreenRecentlyAddedChannelsSize": settingsHome.recentlyAddedChannelsSizeSpinBoxValue,
                "homeScreenRecentlyAddedChannelsAutoScrollDelaySeconds": settingsHome.recentlyAddedChannelsAutoScrollDelaySecondsSpinBoxValue
            }
            settingsController.save(settingsDataPayload)
        }
    }

    Connections {
        target: confirmDialog
        function onAccepted() {
            SettingsController.confirmReset()
        }
        function onRejected() {
            confirmDialog.close()
        }
    }

    // After save/cancel/reset, reload every page control from the service.
    // Connections {
    //     target: SettingsController
    //     function onSaveCompleted() {
    //         SettingsReload.reloadAllPages(root);
    //     }
    //     function onCancelCompleted() {
    //         SettingsReload.reloadAllPages(root);
    //     }
    //     function onResetCompleted() {
    //         SettingsReload.reloadAllPages(root);
    //     }
    // }
}
