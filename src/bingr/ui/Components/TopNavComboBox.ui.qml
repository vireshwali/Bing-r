
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui
import QtQuick.Studio.DesignEffects

Item {
    id: root
    width: 150
    height: 40

    property var model

    property alias comboBox: comboBox

    // external model override; falls back to defaultModel
    ListModel {
        id: defaultModel

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

    ComboBox {
        id: comboBox
        anchors.fill: parent
        model: root.model || defaultModel
        textRole: "text"
        currentIndex: 0
        implicitContentWidthPolicy: ComboBox.WidestText
        indicator: Item {}

        background: Rectangle {
            color: Constants.barBackgroundColorLeftNav
            border.color: Constants.borderColorComboBox
            radius: 10
        }

        contentItem: Text {
            text: comboBox.currentText
            color: Constants.textColorPrimary
            font.pixelSize: 12
            leftPadding: 8
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        popup: Popup {
            y: comboBox.y
            width: comboBox.width
            padding: 0
            background: Rectangle {
                //color: "#434343"
                border.color: Constants.accent
                radius: 6
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight > 300 ? 300 : contentHeight
                model: comboBox.delegateModel
                currentIndex: comboBox.highlightedIndex
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    background: Rectangle {
                        color: "transparent"
                    }
                    contentItem: Rectangle {
                        radius: 3
                        color: "#444"
                        implicitWidth: 4
                    }
                }
            }
        }

        delegate: ItemDelegate {
            id: delegateItem
            width: comboBox.width
            height: 36
            ToolTip.text: model.text
            ToolTip.delay: 600
            ToolTip.visible: delegateItem.hovered
            contentItem: Text {
                text: model.text
                color: comboBox.currentIndex
                       === index ? Constants.accent : Constants.textColorPrimary
                font.pixelSize: 12
                leftPadding: 8
                rightPadding: 8
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                // Hover shade - hardcoded for now
                color: (comboBox.highlightedIndex === index) ? Constants.backgroundColorComboBoxHoverItem : Constants.backgroundColorComboBoxItem
            }
        }
    }
}
