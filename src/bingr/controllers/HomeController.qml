import QtQuick

/*
Design-time stand-in for the Python HomeController type
(bingr.controllers/homeController.py).

Qt Design Studio cannot load PySide6 Python types, so this file mirrors the
C++ type's QML API (signals, properties) to keep Design Studio forms error-free.
It is shadowed at runtime by the qmldir entry that maps HomeController
to homeController.py and is never instantiated by the application.
*/

QtObject {
    //signal loadingChanged(bool isLoading)
    signal channelsExistInApp(bool channelsExist)
    signal channelIdToPlay(int channelId)

    function channelIdPlayRequested(channelId: int): void {}

    property bool loading: false
    property var allChannelsModel: null
    property var continueWatchingChannelsViewModel: null
    property var recentlyAddedChannelsViewModel: null
    property var pagerViewModel1: null
    property var pagerViewModel1SectionTitle: ""
    property var pagerViewModel2: null
    property var pagerViewModel2SectionTitle: ""
    property var pagerViewModel3: null
    property var pagerViewModel3SectionTitle: ""
    property var pagerViewModel4: null
    property var pagerViewModel4SectionTitle: ""
}
