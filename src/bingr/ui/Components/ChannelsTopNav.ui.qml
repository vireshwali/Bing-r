
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
import bingr.controllers 1.0

Item {
    id: root
    width: 1300
    height: 55 // same as height of the openleftnav button

    //the parent screen provides this to a
    //ccomodate the left nav drawer Button on ui
    property int leftMargin: 8
    property var channelsController: null //instance of ChannelsController

    property alias filterSubmitBtn: filterSubmitBtn

    Rectangle {
        id: mainRect
        color: Constants.backgroundColor
        anchors.fill: parent

        // Left section: title, divider, 4 combo boxes
        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: addChannelsBtn.left
            anchors.rightMargin: 8
            spacing: 14

            Text {
                text: qsTr("Channels")
                color: Constants.textColorScreenTitle
                font.pixelSize: 22
                font.weight: Font.Bold
                anchors.verticalCenter: parent.verticalCenter
            }

            // Divider
            Rectangle {
                width: 1
                height: parent.height - 10
                color: Constants.backgroundColorSeparatorRect
                anchors.verticalCenter: parent.verticalCenter
            }

            // Category
            TopNavComboBox {
                id: catCombo
                width: 130
                model: root.channelsController.categoryFilterModel
                comboBox.currentIndex: root.channelsController.categoryFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: catCombo.comboBox
                    function onCurrentIndexChanged() {
                        console.log("catCombo curr index: " + catCombo.comboBox.currentIndex)
                        root.channelsController.categoryFilterModel.currentIndex
                                = catCombo.comboBox.currentIndex
                    }
                }
            }

            // Country
            TopNavComboBox {
                id: countryCombo
                width: 150
                model: root.channelsController.countryFilterModel
                comboBox.currentIndex: root.channelsController.countryFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: qualityCombo.comboBox
                    function onCurrentIndexChanged() {
                        root.channelsController.qualityFilterModel.currentIndex
                                = qualityCombo.comboBox.currentIndex
                    }
                }
            }

            // Quality
            TopNavComboBox {
                id: qualityCombo
                width: 100
                model: root.channelsController.qualityFilterModel
                comboBox.currentIndex: root.channelsController.qualityFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: countryCombo.comboBox
                    function onCurrentIndexChanged() {
                        root.channelsController.countryFilterModel.currentIndex
                                = countryCombo.comboBox.currentIndex
                    }
                }
            }

            IconButton {
                id: filterSubmitBtn
                height: 36
                anchors.verticalCenter: parent.verticalCenter
                btnImageSource: Qt.resolvedUrl("../images/funnel.svg")
                btnImageSize: 26
                btnShadowBlur: 6

                Connections {
                    target: filterSubmitBtn.buttonMouseArea
                    function onClicked() {
                        root.channelsController.applyFilters()
                    }
                }
            }
        }
        IconButtonWithText {
            id: addChannelsBtn
            height: 36
            anchors.right: channelsSearch.left
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            btnImageSize: 28
            btnRadius: 18
            btnShadowBlur: 4
            btnShadowSpread: 4
        }

        // Right section: search field
        CustomTextInputFieldWithIcon {
            id: channelsSearch
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 300
            placeholderText: qsTr("Search channels...")
            imageSource: "../images/search.svg"

            Connections {
                target: channelsSearch.textInput
                function onAccepted() {
                    root.channelsController.applyFiltersWithSearch(
                                channelsSearch.textInput.text)
                }
            }

            Connections {
                target: channelsSearch.buttonMouseArea
                function onClicked() {
                    root.channelsController.applyFiltersWithSearch(
                                channelsSearch.textInput.text)
                }
            }
        }
    }
}
