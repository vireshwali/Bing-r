
/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui

Dialog {
    id: root
    width: 480
    height: 200
    modal: true
    dim: true
    anchors.centerIn: parent
    standardButtons: Dialog.NoButton
    closePolicy: Dialog.NoAutoClose

    // Customizable labels / content
    property string dialogTitle: qsTr("Confirm")
    property string dialogMessage: qsTr("Are you sure?")
    property string okText: qsTr("Confirm")
    property string cancelText: qsTr("Cancel")
    property bool destructive: false

    // Export the buttons for external bindings (hover styling, etc.)
    property alias okButton: okBtn
    property alias cancelButton: cancelBtn

    background: Rectangle {
        color: Constants.barBackgroundColorLeftNav
        radius: 12
        border.width: 1
        border.color: Constants.borderColorComboBox
    }

    contentItem: Rectangle {
        color: "transparent"

        Rectangle {
            anchors.fill: parent
            color: "transparent"

            Text {
                id: titleText
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 20
                anchors.topMargin: 18
                anchors.right: parent.right
                anchors.rightMargin: 20
                text: root.dialogTitle
                color: Constants.textColorScreenTitle
                font.pixelSize: 18
                font.weight: Font.Bold
                elide: Text.ElideRight
            }

            Text {
                id: messageText
                anchors.left: parent.left
                anchors.top: titleText.bottom
                anchors.topMargin: 14
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 20
                text: root.dialogMessage
                color: Constants.textColorPrimary
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                fontSizeMode: Text.VerticalFit
                elide: Text.ElideRight
                verticalAlignment: Text.AlignTop
            }
        }
    }

    footer: Row {
        id: footerRow
        rightPadding: 16
        bottomPadding: 14
        leftPadding: 16
        topPadding: 4
        spacing: 10

        Item {
            id: cancelBtn
            width: 110
            height: 34

            Rectangle {
                id: cancelRect
                anchors.fill: parent
                color: Constants.backgroundColorTableHeader
                radius: 8
                border.width: 1
                border.color: Constants.borderColorComboBox

                Text {
                    anchors.centerIn: parent
                    text: root.cancelText
                    color: Constants.textColorPrimary
                    font.pixelSize: 12
                }

                MouseArea {
                    id: cancelMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.reject()
                }
            }

            // states: [
            //     State {
            //         name: "Hovered"
            //         when: cancelMouseArea.containsMouse
            //         PropertyChanges {
            //             target: cancelRect
            //             color: Constants.borderColorComboBox
            //         }
            //     }
            // ]
        }

        Item {
            id: okBtn
            width: 110
            height: 34

            Rectangle {
                id: okRect
                anchors.fill: parent
                color: root.destructive ? "#c0392b" : Constants.accent
                radius: 8

                Text {
                    anchors.centerIn: parent
                    text: root.okText
                    color: "#ffffff"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    id: okMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.accept()
                }
            }

            // states: [
            //     State {
            //         name: "Hovered"
            //         when: okMouseArea.containsMouse
            //         PropertyChanges {
            //             target: okRect
            //             opacity: 0.85
            //         }
            //     }
            // ]
        }
    }
}
