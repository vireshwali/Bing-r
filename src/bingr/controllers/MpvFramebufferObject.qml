import QtQuick

/*
Design-time stand-in for the Python MpvFramebufferObject type
(bingr.controllers/mainPlayerController.py).

Qt Design Studio cannot load PySide6 Python types, so this file mirrors the
C++ type's QML API (properties, signals, slots) to keep Design Studio forms
error-free. It is shadowed at runtime by the qmldir entry that maps
MpvFramebufferObject to mainPlayerController.py and is never instantiated
by the application.
*/

QtObject {
    property bool mirrorVertically: false
    property bool textureFollowsItemSize: true

    signal request_update
    signal onSurfaceReady
    signal bufferedSecondsChanged(real seconds)
    signal readaheadSecsChanged(real seconds)
    signal bufferingStateChanged(string state)
    signal errorOccurred(string error, string fatal)

    function doUpdate(): void {
    }

    function setMediaUrl(url: string): void {
    }

    function setPlaying(playing: bool): void {
    }

    function stop(): void {
    }

    function setVolume(vol: int): void {
    }
}
