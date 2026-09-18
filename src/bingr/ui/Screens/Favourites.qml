
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
import bingr.controllers

Item {
    id: root
    width: 800
    height: 800

    property int topNavLeftMargin: 8
    property alias favoritesController: favoritesController
    property string starterMsg: qsTr("You don't have any favourite channels yet.<br />Hit the heart button on channels to start adding your favourites.")
    property bool channelsExist: true

    Component.onCompleted: {
        console.log("Favorites onCompleted called.")
    }

    Component.onDestruction: {
        console.log("Favorites onDestruction called.")
    }

    FavoritesController {
        id: favoritesController
    }

    Connections {
        target: favoritesController
        function onChannelsExistInApp(channelsExist) {
            root.channelsExist = channelsExist
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Constants.backgroundColor

        Text {
            id: starterMsgLabel
            width: parent.width * 0.8
            text: root.starterMsg
            font.letterSpacing: 0.2
            anchors.centerIn: parent
            color: Constants.textColorSecondary
            font.pixelSize: 24
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignTop
            lineHeight: 1.4
            wrapMode: Text.WordWrap
            font.wordSpacing: 0
            font.bold: true
            visible: !root.channelsExist
        }

        FavoritesTopNav {
            id: favouritesTopNav
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: root.topNavLeftMargin
            anchors.right: parent.right
        }

        ChannelsGrid {
            id: favouritesGrid
            anchors.left: parent.left
            anchors.top: favouritesTopNav.bottom
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            gridController: favoritesController
            visible: root.channelsExist
        }
    }
}
