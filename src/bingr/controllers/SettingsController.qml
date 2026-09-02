pragma Singleton
import QtQuick

QtObject {
    property var service: null

    function getValue(key: string): var { return ""; }
    function defaultValue(key: string): var { return ""; }
    function onValueChanged(key: string, value: var) {}
    function save() {}
    function cancel() {}
    function requestReset() {}
    function confirmReset() {}
}