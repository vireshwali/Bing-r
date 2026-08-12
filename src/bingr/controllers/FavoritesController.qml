import QtQuick

/*
Design-time stand-in for the Python FavoritesController type
(bingr.controllers/favoritesController.py).

Qt Design Studio cannot load PySide6 Python types, so this file mirrors the
C++ type's QML API (signals, slots) to keep Design Studio forms error-free.
It is shadowed at runtime by the qmldir entry that maps FavoritesController
to favoritesController.py and is never instantiated by the application.
*/

QtObject {
    function toggleFavorite(channelId: int): void {
    }
}
