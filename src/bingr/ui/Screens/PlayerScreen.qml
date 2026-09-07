import QtQuick
import QtQuick.Controls
import "../Components"
import bingr.controllers

Item {
    id: root
    anchors.fill: parent
    focus: true

    property int channelId: -1
    property bool isFullScreen: false

    signal closed

    Keys.onEscapePressed: {
        mainPlayer.videoItem.stop();
        mainPlayerController.stop();
        root.closed();
    }

    Rectangle {
        id: playerOverlay
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.6)

        MouseArea {
            anchors.fill: parent
            onClicked: {
                mainPlayer.videoItem.stop();
                mainPlayerController.stop();
                root.closed();
            }
        }
    }

    Item {
        id: videoPanel
        width: root.isFullScreen ? parent.width : Math.min(parent.width * 0.6, 1200)
        height: root.isFullScreen ? parent.height : width * 9 / 16
        x: root.isFullScreen ? 0 : parent.width - width - 20
        y: root.isFullScreen ? 0 : 20

        Behavior on width {
            NumberAnimation {
                duration: 300
            }
        }
        Behavior on height {
            NumberAnimation {
                duration: 300
            }
        }
        Behavior on x {
            NumberAnimation {
                duration: 300
            }
        }
        Behavior on y {
            NumberAnimation {
                duration: 300
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                var playing = !mainPlayerController.playing;
                mainPlayerController.setPlaying(playing);
                mainPlayer.videoItem.setPlaying(playing);
            }
        }

        MainPlayer {
            id: mainPlayer
            anchors.fill: parent
            streamsViewModel: mainPlayerController.streamsViewModel
            currentStreamIndex: mainPlayerController.currentStreamIndex
            subtitlesViewModel: mainPlayerController.subtitlesViewModel
            currentSubtitleIndex: mainPlayerController.currentSubtitleIndex
            isFullScreen: root.isFullScreen
        }

        CommonDialog {
            id: errorDialog
            anchors.centerIn: parent
            visible: false
            dialogTitleImg: Qt.resolvedUrl("../images/help-circle.svg")
            z: 10
        }

        Connections {
            target: errorDialog
            function onClosed() {
                errorDialog.visible = false;
                mainPlayer.loading = false;
                if (mainPlayerController.hasMultipleStreams) {
                    // More URLs available: keep player open so user can switch streams.
                    console.log("Player error dismissed — user can try another stream");
                } else {
                    // Only one URL: close and dispose the player entirely.
                    mainPlayer.videoItem.stop();
                    mainPlayerController.stop();
                    root.closed();
                    console.log("Player disposed after error dialog close");
                }
            }
        }
    }

    MainPlayerController {
        id: mainPlayerController
    }

    //auto generated handler for property channelId
    //mapped to the this conenction by QT internally
    Connections {
        target: root
        function onChannelIdChanged() {
            console.log("onChannelIdChanged " + root.channelId);
            errorDialog.visible = false;
            if (root.channelId !== -1) {
                mainPlayerController.channelId = root.channelId;
                mainPlayerController.openChannel(root.channelId);
            }
        }
    }

    Connections {
        target: mainPlayerController
        function onPlayUrlRequested(url) {
            console.log("playUrlRequested " + url);
            if (mainPlayer.videoItem) {
                mainPlayer.loading = true;
                mainPlayer.volumeSlider.value = 50;
                mainPlayer.videoItem.setMediaUrl(url);
                mainPlayer.videoItem.setVolume(mainPlayerController.volume);
                mainPlayer.videoItem.setPlaying(true);
                mainPlayerController.setPlaying(true);
            }
        }
    }

    Connections {
        target: mainPlayer.videoItem
        function onBufferingStateChanged(state) {
            mainPlayer.loading = state !== "playing";
        }
        function onErrorOccurred(message, details) {
            console.log("Player error: " + message);
            mainPlayer.loading = false;
            errorDialog.dialogTitle = message;
            var hint = "";
            if (mainPlayerController.hasMultipleStreams) {
                hint = "\n\nTry another stream from the dropdown.";
            }
            errorDialog.dialogMsg = details + hint;
            errorDialog.dialogMsgToolTip = details + hint;
            errorDialog.visible = true;
        }
    }

    Connections {
        target: mainPlayer.playBtn.buttonMouseArea
        function onClicked() {
            var playing = !mainPlayerController.playing;
            mainPlayerController.setPlaying(playing);
            mainPlayer.videoItem.setPlaying(playing);
        }
    }

    Connections {
        target: mainPlayer.stopBtn.buttonMouseArea
        function onClicked() {
            mainPlayer.videoItem.stop();
            mainPlayerController.stop();
            root.closed();
        }
    }

    Connections {
        target: mainPlayer.fullScreenBtn.buttonMouseArea
        function onClicked() {
            root.isFullScreen = !root.isFullScreen;
        }
    }

    Connections {
        target: mainPlayer.streamsComboBox
        function onActivated(index) {
            mainPlayerController.switchStream(index);
        }
    }

    Connections {
        target: mainPlayer
        function onSubtitleActivated(index) {
            mainPlayerController.switchSubtitle(index);
        }
    }

    Connections {
        target: mainPlayer.videoItem
        function onSubtitleTracksChanged(tracks) {
            mainPlayerController.updateSubtitleTracks(tracks);
        }
    }

    Connections {
        target: mainPlayerController
        function onSubtitleTrackChanged(trackId) {
            if (mainPlayer.videoItem) {
                mainPlayer.videoItem.setSubtitleTrack(trackId);
            }
        }
    }

    Connections {
        target: mainPlayerController
        function onPlayingChanged() {
            if (mainPlayerController.playing) {
                mainPlayer.playBtn.btnImageSource = Qt.resolvedUrl("../images/pause.svg");
                mainPlayer.playBtn.btnTooptipText = qsTr("Pause");
            } else {
                mainPlayer.playBtn.btnImageSource = Qt.resolvedUrl("../images/play.svg");
                mainPlayer.playBtn.btnTooptipText = qsTr("Play");
            }
        }
    }

    Connections {
        target: mainPlayer.volumeSlider
        function onValueChanged() {
            mainPlayerController.setVolume(mainPlayer.volumeSlider.value);
        }
    }

    Connections {
        target: mainPlayerController
        function onVolumeChanged() {
            var vol = mainPlayerController.volume;
            if (mainPlayer.videoItem) {
                mainPlayer.videoItem.setVolume(vol);
            }
        }
    }
}
