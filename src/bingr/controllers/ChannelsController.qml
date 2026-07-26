pragma Singleton
import QtQuick

QtObject {
    property var channelsHeroViewModel: null
    property var channelsViewModel: null

    function loadChannels() {}
    function applyFilters(category: string, quality: string, country: string, search: string) {}
}
