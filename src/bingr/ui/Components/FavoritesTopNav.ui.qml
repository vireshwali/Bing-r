
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
    width: 800
    height: 40 // same as height of the openleftnav button

    //the parent screen provides this to a
    //ccomodate the left nav drawer Button on ui
    property int leftMargin: 8

    Rectangle {
        id: mainRect
        color: Constants.backgroundColor
        anchors.fill: parent

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: qsTr("Favourites")
            color: Constants.textColorScreenTitle
            font.pixelSize: 22
            font.weight: Font.Bold
        }

        // Right section: search field
        CustomTextInputFieldWithIcon {
            id: favouritesSearch
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 300
            placeholderText: qsTr("Search favourites...")
            imageSource: "../images/search.svg"

            Connections {
                target: favouritesSearch.textInput
                function onAccepted() {
                    console.log(favouritesSearch.textInput.text)
                }
            }

            Connections {
                target: favouritesSearch.buttonMouseArea
                function onClicked() {
                    console.log(favouritesSearch.textInput.text)
                }
            }
        }
    }
}
