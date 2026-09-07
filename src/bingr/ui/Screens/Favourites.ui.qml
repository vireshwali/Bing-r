
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

    FavoritesController {
        id: favoritesController
    }

    Rectangle {
        anchors.fill: parent
        color: Constants.backgroundColor

        FavoritesTopNav {
            id: favouritesTopNav
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: 10
            anchors.leftMargin: root.topNavLeftMargin
            anchors.right: parent.right
        }

        ChannelsGrid {
            id: favouritesGrid
            anchors.left: parent.left
            anchors.top: favouritesTopNav.bottom
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            channelsModel: favoritesController.favoritesGridViewModel
            gridController: favoritesController
        }
    }
}
