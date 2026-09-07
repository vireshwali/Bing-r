
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
    width: 1000
    height: 40 // same as height of the openleftnav button

    //the parent screen provides this to a
    //ccomodate the left nav drawer Button on ui
    property int leftMargin: 8

    property alias filterSubmitBtn: filterSubmitBtn

    // Hardcoded models for 4 combo boxes
    ListModel {
        id: categoryModel

        ListElement {
            text: "All Categories"
        }
        ListElement {
            text: "Business"
        }
        ListElement {
            text: "Culture"
        }
        ListElement {
            text: "Documentary"
        }
        ListElement {
            text: "Education"
        }
        ListElement {
            text: "Entertainment"
        }
        ListElement {
            text: "Family"
        }
        ListElement {
            text: "General"
        }
        ListElement {
            text: "Kids"
        }
        ListElement {
            text: "Lifestyle"
        }
        ListElement {
            text: "Movies"
        }
        ListElement {
            text: "Music"
        }
        ListElement {
            text: "News"
        }
        ListElement {
            text: "Religious"
        }
        ListElement {
            text: "Sports"
        }
    }

    ListModel {
        id: countryModel

        ListElement {
            text: "All Countries"
        }
        ListElement {
            text: "United States of America"
        }
        ListElement {
            text: "United Kingdom of the great log country here"
        }
        ListElement {
            text: "India"
        }
        ListElement {
            text: "Canada"
        }
        ListElement {
            text: "Australia"
        }
        ListElement {
            text: "Germany"
        }
        ListElement {
            text: "France"
        }
        ListElement {
            text: "Japan"
        }
        ListElement {
            text: "Brazil"
        }
    }

    ListModel {
        id: cityModel

        ListElement {
            text: "All Cities"
        }
        ListElement {
            text: "Saganisoninmonzenzenkōjiyamachō"
        }
        ListElement {
            text: "Pekwachnamaykoskwaskwaypinwanik asdasd"
        }
        ListElement {
            text: "Äteritsiputeritsipuolilautatsijänkä asdasd"
        }
        ListElement {
            text: "Azpilikuetagaraikosaroiarenberekolarrea    asdad"
        }
        ListElement {
            text: "Sydney"
        }
        ListElement {
            text: "Berlin"
        }
        ListElement {
            text: "Paris"
        }
        ListElement {
            text: "Tokyo"
        }
        ListElement {
            text: "São Paulo"
        }
    }

    ListModel {
        id: qualityModel

        ListElement {
            text: "All Qualities"
        }
        ListElement {
            text: "4K"
        }
        ListElement {
            text: "HD"
        }
        ListElement {
            text: "SD"
        }
    }

    Rectangle {
        id: mainRect
        color: Constants.backgroundColor
        anchors.fill: parent

        // Left section: title, divider, 4 combo boxes
        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: channelsSearch.left
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
                //model: categoryModel
                model: ChannelsController.categoryFilterModel
                comboBox.currentIndex: ChannelsController.categoryFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: catCombo.comboBox
                    function onCurrentIndexChanged() {
                        console.log("catCombo curr index: " + catCombo.comboBox.currentIndex)
                        ChannelsController.categoryFilterModel.currentIndex
                                = catCombo.comboBox.currentIndex
                    }
                }
            }

            // Country
            TopNavComboBox {
                id: countryCombo
                width: 150
                //model: countryModel
                model: ChannelsController.countryFilterModel
                comboBox.currentIndex: ChannelsController.countryFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: qualityCombo.comboBox
                    function onCurrentIndexChanged() {
                        ChannelsController.qualityFilterModel.currentIndex
                                = qualityCombo.comboBox.currentIndex
                    }
                }
            }

            // City
            // TopNavComboBox {
            //     id: cityCombo
            //     width: 200
            //     model: cityModel
            //     anchors.verticalCenter: parent.verticalCenter
            // }

            // Quality
            TopNavComboBox {
                id: qualityCombo
                width: 100
                //model: qualityModel
                model: ChannelsController.qualityFilterModel
                comboBox.currentIndex: ChannelsController.qualityFilterModel.currentIndex
                anchors.verticalCenter: parent.verticalCenter

                Connections {
                    target: countryCombo.comboBox
                    function onCurrentIndexChanged() {
                        ChannelsController.countryFilterModel.currentIndex
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
                        ChannelsController.applyFilters()
                    }
                }
            }
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
                    ChannelsController.applyFiltersWithSearch(channelsSearch.textInput.text)
                }
            }

            Connections {
                target: channelsSearch.buttonMouseArea
                function onClicked() {
                    ChannelsController.applyFiltersWithSearch(channelsSearch.textInput.text)
                }
            }
        }
    }
}
