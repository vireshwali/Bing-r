pragma Singleton

import QtQuick
import QtQuick.Studio.Application

QtObject {
    readonly property int width: 1480
    readonly property int height: 900
    readonly property int minimumWidth: 1280
    readonly property int minimumHeight: 800

    property string relativeFontDirectory: "fonts"

    /* Edit this comment to add your custom font */
    readonly property font font: Qt.font({
        "family": Qt.application.font.family,
        "pixelSize": Qt.application.font.pixelSize
    })
    readonly property font largeFont: Qt.font({
        "family": Qt.application.font.family,
        "pixelSize": Qt.application.font.pixelSize * 1.6
    })

    readonly property color accent: '#e6931f'
    readonly property color liveGreen: '#32f820'

    readonly property color qualitySD: '#e7e7e7'
    readonly property color qualityHD: '#e0ee16'
    readonly property color qualityFHD: '#0ce9e9'
    readonly property color qualityQHD: '#8ae414'
    readonly property color quality4K: '#f09c20'
    readonly property color qualityUHD: quality4K
    readonly property color quality8K: '#ef4217'

    // Backgrounds and Borders
    readonly property color backgroundColor: '#121212'
    readonly property color barBackgroundColorLeftNav: '#0f0f0f'
    readonly property color barBackgroundColorStatusBar: '#0a0a0a'
    readonly property color backgroundColorTableHeader: '#2d2d2d'
    readonly property color borderColorTableHeader: '#353535'
    readonly property color backgroundColorTableCell: '#1a1a1a'
    readonly property color borderColorTableCell: '#2c2c2c'
    readonly property color backgroundColorSeparatorRect: "#444444"

    readonly property color backgroundColorComboBox: barBackgroundColorLeftNav
    readonly property color borderColorComboBox: '#3a3a3a'
    readonly property color backgroundColorComboBoxItem: backgroundColorTableCell
    readonly property color backgroundColorComboBoxHoverItem: borderColorTableHeader

    readonly property color backgroundColorWatchNowPlayIcon: borderColorTableHeader
    readonly property color backgroundColorHeroLogoPlaceholder: backgroundColorTableHeader
    readonly property color backgroundChannelsGridCardBg: backgroundColorTableCell
    readonly property color backgroundChannelsGridCardLogoBg: '#444444'

    // Text colors
    readonly property color textColorPrimary: '#c1c1c1'
    readonly property color textColorSecondary: '#b3b3b3'
    readonly property color textColorMuted: '#a0a0a0'
    readonly property color textColorScreenTitle: "#eaeaea"
    readonly property color textColorTableHeader: '#b1b1b1'
    readonly property color textColorChannelsHeroLabels: '#bfbfbf'

    // Text csizes
    readonly property int textFontPixelSizeUpper3: 20
    readonly property int textFontPixelSizeUpper2: 18
    readonly property int textFontPixelSizeUpper1: 16
    readonly property int textFontPixelSizeDefault: 14
    readonly property int textFontPixelSizeLower1: 13
    readonly property int textFontPixelSizeLower2: 12
    readonly property int textFontPixelSizeLower3: 11
    readonly property int textFontPixelSizeHeroChannelName: 34
    readonly property int textFontPixelSizeHeroChannelAltName: 20

    property StudioApplication application: StudioApplication {
        fontPath: Qt.resolvedUrl("../ui/" + relativeFontDirectory)
    }

    // Default values for component properties
    property double defaultTooltipDelay: 1500
    property double defaultTooltipTimeout: 40000
}
