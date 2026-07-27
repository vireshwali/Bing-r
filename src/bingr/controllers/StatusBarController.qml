pragma Singleton
import QtQuick

QtObject {
    signal progressMsg(string msg)
    signal internetStatus(string msg, string msgType)
    signal diskStatus(string msg, string msgType)
    signal ramStatus(string msg, string msgType)

    signal channelsMsg(string msg)
    signal favouritesMsg(string msg)
    signal playlistsMsg(string msg)
}
