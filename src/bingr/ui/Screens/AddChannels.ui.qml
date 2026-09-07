import QtQuick
import QtQuick.Controls
import ui
import "../Components"
import QtQuick.Studio.DesignEffects
import bingr.controllers

Item {
    id: root
    width: Constants.width
    height: Constants.height

    property int inputMode: 0
    property int selectedFileCount: 0
    property bool importing: false

    readonly property color filesDropAreaRectColor: "#181818"
    readonly property color filesDropAreaRectBorderColor: "#323232"

    AddNewSourcesController {
        id: addNewSourcesController
    }

    Rectangle {
        id: rectangle
        anchors.fill: parent
        color: Constants.backgroundColor

        Text {
            id: headerLabel
            text: qsTr("Add IPTV Channels")
            anchors.top: parent.top
            anchors.topMargin: 20
            color: Constants.textColorScreenTitle
            font.pixelSize: 22
            anchors.horizontalCenterOffset: 0
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            id: contectAreaRect
            color: Constants.backgroundColor
            anchors.verticalCenterOffset: 16
            width: rectangle.width * 0.65
            height: rectangle.height * 0.8
            anchors.centerIn: parent

            Column {
                id: columnView
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                rightPadding: 12
                leftPadding: 12
                spacing: 24

                Rectangle {
                    id: filesDropRect
                    width: parent.width * 0.4
                    height: 125
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: root.filesDropAreaRectColor
                    border.color: root.filesDropAreaRectBorderColor

                    Image {
                        id: image1
                        width: 40
                        height: 40
                        source: "../images/files-size-64.svg"
                        anchors.verticalCenterOffset: -14
                        sourceSize.height: 64
                        sourceSize.width: 64
                        fillMode: Image.PreserveAspectFit
                        anchors.centerIn: parent
                    }

                    DesignEffect {
                        effects: [
                            DesignDropShadow {
                                color: "#252525"
                                offsetY: 1
                                blur: 18
                                spread: 8
                            }
                        ]
                    }

                    Text {
                        id: text1
                        color: Constants.textColorPrimary
                        text: qsTr("Drop your m3u files here for processing.")
                        font.pixelSize: 14
                        anchors.top: image1.bottom
                        anchors.topMargin: 8
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    DropArea {
                        id: filesDropArea
                        anchors.fill: parent
                    }

                    Connections {
                        target: filesDropArea
                        function onDropped(drop: DragEvent) {
                            if (!drop.hasUrls) {
                                drop.accepted = false
                                return
                            }
                            let count = 0
                            for (var i = 0; i < drop.urls.length; i++) {
                                let urlStr = drop.urls[i].toString()
                                let fileName = urlStr.split('/').pop()
                                if (fileName.toLowerCase().endsWith('.m3u')
                                        || fileName.toLowerCase().endsWith(
                                            '.m3u8')) {
                                    count++
                                }
                            }
                            //root.selectedFileCount = count
                            addNewSourcesController.processM3UFiles(drop.urls)
                            if (count === 0)
                                drop.accepted = false
                        }
                    }
                }

                Row {
                    id: row1
                    width: parent.width * 0.6
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 12

                    // Left Line
                    Rectangle {
                        height: 1
                        width: (parent.width - textOr.implicitWidth - row1.spacing) / 2
                        anchors.verticalCenter: parent.verticalCenter
                        color: "#444444"
                        border.width: 0
                    }

                    // Center Text
                    Text {
                        id: textOr
                        text: "Or"
                        anchors.verticalCenter: parent.verticalCenter
                        font.bold: true
                        color: "#888888"
                        font.pixelSize: 14
                    }

                    // Right Line
                    Rectangle {
                        height: 1
                        width: (parent.width - textOr.implicitWidth - row1.spacing) / 2
                        anchors.verticalCenter: parent.verticalCenter
                        color: "#444444"
                    }
                }

                Column {
                    id: urlsInputColumn
                    width: parent.width * 0.8
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 11

                    Text {
                        id: urlsInptText
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: Constants.textColorPrimary
                        text: qsTr("Add upto 4 URLs to process.")
                        font.pixelSize: 14
                    }

                    CustomTextInputFieldWithIcon {
                        id: customTextInput1
                        width: parent.width * 0.8
                        anchors.horizontalCenter: parent.horizontalCenter
                        placeholderText: qsTr(
                                             "Type or Paste your M3U url here.")
                        shadowBlur: 1
                        shadowSpreadSize: 1
                    }

                    CustomTextInputFieldWithIcon {
                        id: customTextInput2
                        width: parent.width * 0.8
                        anchors.horizontalCenter: parent.horizontalCenter
                        placeholderText: qsTr(
                                             "Type or Paste your M3U url here.")
                        shadowBlur: 1
                        shadowSpreadSize: 1
                    }
                    CustomTextInputFieldWithIcon {
                        id: customTextInput3
                        width: parent.width * 0.8
                        anchors.horizontalCenter: parent.horizontalCenter
                        placeholderText: qsTr(
                                             "Type or Paste your M3U url here.")
                        shadowBlur: 1
                        shadowSpreadSize: 1
                    }
                    CustomTextInputFieldWithIcon {
                        id: customTextInput4
                        width: parent.width * 0.8
                        anchors.horizontalCenter: parent.horizontalCenter
                        placeholderText: qsTr(
                                             "Type or Paste your M3U url here.")
                        shadowBlur: 1
                        shadowSpreadSize: 1
                    }
                }

                IconButtonWithText {
                    id: addUrlsBtn
                    anchors.horizontalCenter: parent.horizontalCenter
                    btnText: qsTr("Add Urls")

                    Connections {
                        target: addUrlsBtn.buttonMouseArea
                        function onClicked() {
                            let urlsArray = []
                            let url1 = customTextInput1.textInput.text
                            let url2 = customTextInput2.textInput.text
                            let url3 = customTextInput3.textInput.text
                            let url4 = customTextInput4.textInput.text

                            if ((url1 !== null) && (url1 !== undefined)
                                    && (url1 !== "")) {
                                urlsArray.push(url1)
                            }

                            if ((url2 !== null) && (url2 !== undefined)
                                    && (url2 !== "")) {
                                urlsArray.push(url2)
                            }

                            if ((url3 !== null) && (url3 !== undefined)
                                    && (url3 !== "")) {
                                urlsArray.push(url3)
                            }

                            if ((url4 !== null) && (url4 !== undefined)
                                    && (url4 !== "")) {
                                urlsArray.push(url4)
                            }

                            if (urlsArray.length > 0) {
                                addNewSourcesController.processM3UFiles(
                                            urlsArray)
                            }
                        }
                    }
                }
            }

            Item {
                id: resultsSection
                width: parent.width
                visible: true
                anchors.top: columnView.bottom
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter

                SeparatorRect {
                    id: separatorRect
                    height: 1
                    width: parent.width * 0.6
                    anchors.top: parent.top
                    anchors.topMargin: columnView.spacing
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                GridView {
                    id: resultsGridView
                    width: parent.width * 0.8
                    //height: 120
                    visible: true
                    anchors.top: separatorRect.bottom
                    anchors.topMargin: columnView.spacing
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom

                    cellWidth: width
                    cellHeight: 40
                    clip: true
                    model: addNewSourcesController.sourcesProcessingStatusViewModel
                    header: Item {
                        width: resultsGridView.width
                        height: resultsGridView.cellHeight

                        Row {
                            anchors.fill: parent

                            Rectangle {
                                width: parent.width * 0.05
                                height: parent.height
                                color: Constants.backgroundColorTableHeader
                                border.color: Constants.borderColorTableHeader
                                Text {
                                    anchors.centerIn: parent
                                    text: "#"
                                    font.bold: true
                                    font.pointSize: 11
                                    color: Constants.textColorTableHeader
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Rectangle {
                                width: parent.width * 0.60
                                height: parent.height
                                color: Constants.backgroundColorTableHeader
                                border.color: Constants.borderColorTableHeader
                                Text {
                                    anchors.centerIn: parent
                                    text: "Path / URL"
                                    font.bold: true
                                    font.pointSize: 11
                                    color: Constants.textColorTableHeader
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Rectangle {
                                width: parent.width * 0.35
                                height: parent.height
                                color: Constants.backgroundColorTableHeader
                                border.color: Constants.borderColorTableHeader
                                Text {
                                    anchors.centerIn: parent
                                    text: "Status"
                                    font.bold: true
                                    font.pointSize: 11
                                    color: Constants.textColorPrimary
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }
                    delegate: Item {
                        width: resultsGridView.width
                        height: resultsGridView.cellHeight

                        Row {
                            anchors.fill: parent

                            Rectangle {
                                width: parent.width * 0.05
                                height: parent.height
                                color: Constants.backgroundColorTableCell
                                border.color: Constants.borderColorTableCell
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8
                                    anchors.right: parent.right
                                    anchors.rightMargin: 8
                                    horizontalAlignment: Text.AlignHCenter
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: model.index + 1
                                    elide: Text.ElideMiddle
                                    font.pointSize: 10
                                    color: Constants.textColorPrimary
                                }
                            }

                            Rectangle {
                                width: parent.width * 0.60
                                height: parent.height
                                color: Constants.backgroundColorTableCell
                                border.color: Constants.borderColorTableCell
                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8
                                    anchors.right: parent.right
                                    anchors.rightMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: name
                                    elide: Text.ElideMiddle
                                    font.pointSize: 10
                                    color: Constants.textColorPrimary
                                }
                            }

                            Rectangle {
                                width: parent.width * 0.35
                                height: parent.height
                                color: Constants.backgroundColorTableCell
                                border.color: Constants.borderColorTableCell

                                Text {
                                    anchors.centerIn: parent
                                    anchors.leftMargin: 8
                                    text: status
                                    font.pointSize: 10
                                    color: Constants.textColorPrimary
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }

                    // Attaches the scrollbar with adaptive visibility
                    ScrollBar.vertical: ScrollBar {
                        id: vScrollBar

                        // Shows when moving, hides when stationary
                        policy: ScrollBar.AsNeeded

                        // Keeps the scrollbar inside the right edge of the grid view
                        parent: resultsGridView
                    }
                }
            }
        }
    }
    states: [
        State {
            name: "dragOverState"
            when: filesDropArea.containsDrag
            PropertyChanges {
                target: filesDropRect
                color: "#242424"
            }
        }
    ]
}
