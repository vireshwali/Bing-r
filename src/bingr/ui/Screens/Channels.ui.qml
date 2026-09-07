

/*
This is a UI file (.ui.qml) that is intended to be edited in Qt Design Studio only.
It is supposed to be strictly declarative and only uses a subset of QML. If you edit
this file manually, you might introduce QML code that is not supported by Qt Design Studio.
Check out https://doc.qt.io/qtcreator/creator-quick-ui-forms.html for details on .ui.qml files.
*/
import QtQuick
import QtQuick.Controls
import ui
import "../Components"
import bingr.controllers

Item {
    id: root
    width: 800
    height: 800
    property int topNavLeftMargin: 8

    Rectangle {
        id: rectangle
        anchors.fill: parent
        color: Constants.backgroundColor

        ChannelsTopNav {
            id: channelsTopNav
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: 10
            anchors.leftMargin: root.topNavLeftMargin
            anchors.right: parent.right
        }

        ChannelsHeroSection {
            id: heroSection
            height: parent.height * 0.26
            anchors.left: parent.left
            anchors.top: channelsTopNav.bottom
            anchors.topMargin: 10
            anchors.right: parent.right
            heroModel: ChannelsController.channelsHeroViewModel
        }

        Rectangle {
            id: separatorRect
            height: 1
            color: Constants.accent
            radius: 1
            border.width: 0
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: heroSection.bottom
            anchors.topMargin: 8
            topLeftRadius: 1
        }

        ChannelsGrid {
            id: channelsGrid
            anchors.left: parent.left
            anchors.top: separatorRect.bottom
            anchors.topMargin: 8
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            channelsModel: ChannelsController.channelsViewModel
        }
    }
}
