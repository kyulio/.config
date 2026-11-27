import QtQuick 2.15
import QtQuick.Window 2.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height
    color: "black"

    readonly property string monoFont: "JetBrainsMono Nerd Font"
    property var userNames: []
    property int userIndex: userModel.lastIndex
    property var sessionNames: []
    property int sessionIndex: sessionModel.lastIndex
    property bool busy: false
    property bool failed: false
    property date now: new Date()

    function currentUser() {
        return userNames[userIndex] || userModel.lastUser || userNames[0] || ""
    }

    function submit() {
        if (password.text.length === 0 || busy)
            return
        busy = true
        failed = false
        sddm.login(currentUser(), password.text, sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false
            root.failed = true
            password.text = ""
            shake.restart()
            password.forceActiveFocus()
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Repeater {
        model: userModel
        Item {
            property string userName: name
            Component.onCompleted: {
                var names = root.userNames.slice()
                names[index] = userName
                root.userNames = names
            }
        }
    }

    Repeater {
        id: sessions
        model: sessionModel
        Item {
            property string sessionName: name
            Component.onCompleted: {
                root.sessionNames[index] = sessionName
                root.sessionNamesChanged()
            }
        }
    }

    Image {
        anchors.fill: parent
        source: "background.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.ArrowCursor
        onClicked: password.forceActiveFocus()
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -150
        text: Qt.formatTime(root.now, "HH:mm")
        color: Qt.rgba(1, 1, 1, 0.9)
        font.family: root.monoFont
        font.bold: true
        font.pixelSize: 80
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -80
        text: Qt.locale("en_US").toString(root.now, "dddd, dd MMMM yyyy")
        color: Qt.rgba(200 / 255, 200 / 255, 200 / 255, 0.7)
        font.family: root.monoFont
        font.pixelSize: 18
    }

    ListModel {
        id: dots
    }

    Rectangle {
        id: field
        property real shakeOffset: 0

        Behavior on border.color {
            ColorAnimation { duration: 150 }
        }

        SequentialAnimation {
            id: shake
            NumberAnimation { target: field; property: "shakeOffset"; to: -8; duration: 50 }
            NumberAnimation { target: field; property: "shakeOffset"; to: 8; duration: 70 }
            NumberAnimation { target: field; property: "shakeOffset"; to: -5; duration: 70 }
            NumberAnimation { target: field; property: "shakeOffset"; to: 0; duration: 60 }
        }

        width: 250
        height: 50
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 50
        anchors.horizontalCenterOffset: shakeOffset
        radius: 10
        color: Qt.rgba(0, 0, 0, 0.5)
        border.width: 2
        border.color: root.failed ? "#cc2222" : (root.busy ? Qt.rgba(1, 1, 1, 0.6) : Qt.rgba(1, 1, 1, 0.2))

        TextInput {
            id: password
            anchors.fill: parent
            anchors.margins: 12
            echoMode: TextInput.Password
            color: "transparent"
            selectionColor: "transparent"
            selectedTextColor: "transparent"
            cursorVisible: false
            cursorDelegate: Item {}
            focus: true
            clip: true
            onTextChanged: {
                if (text.length > 0)
                    root.failed = false
                var wanted = Math.min(text.length, 14)
                while (dots.count < wanted)
                    dots.append({})
                while (dots.count > wanted)
                    dots.remove(dots.count - 1)
            }
            Keys.onReturnPressed: root.submit()
            Keys.onEnterPressed: root.submit()
        }

        Text {
            anchors.centerIn: parent
            visible: password.length === 0
            text: root.failed ? "Authentication failed" : "Enter Password..."
            color: root.failed ? "#cc2222" : Qt.rgba(1, 1, 1, 0.55)
            font.family: root.monoFont
            font.italic: true
            font.pixelSize: 14
        }

        Row {
            anchors.centerIn: parent
            spacing: 4
            move: Transition {
                NumberAnimation { property: "x"; duration: 90; easing.type: Easing.OutQuad }
            }
            Repeater {
                model: dots
                Rectangle {
                    width: 12
                    height: 12
                    radius: 6
                    color: "white"
                    scale: 0.3
                    opacity: 0
                    Component.onCompleted: {
                        scale = 1
                        opacity = 1
                    }
                    Behavior on scale {
                        NumberAnimation { duration: 110; easing.type: Easing.OutBack }
                    }
                    Behavior on opacity {
                        NumberAnimation { duration: 90 }
                    }
                }
            }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 24
        spacing: 22

        Text {
            text: "\u{f0004}  " + root.currentUser() + (root.userNames.length > 1 ? "  \u{f0140}" : "")
            color: userArea.containsMouse && root.userNames.length > 1 ? "white" : Qt.rgba(1, 1, 1, 0.55)
            font.family: root.monoFont
            font.pixelSize: 14
            MouseArea {
                id: userArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: root.userNames.length > 1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (root.userNames.length > 1)
                        root.userIndex = (root.userIndex + 1) % root.userNames.length
                    password.forceActiveFocus()
                }
            }
        }

        Text {
            text: "\u{f0379}  " + (root.sessionNames[root.sessionIndex] || "") + "  \u{f0140}"
            color: sessionArea.containsMouse ? "white" : Qt.rgba(1, 1, 1, 0.55)
            font.family: root.monoFont
            font.pixelSize: 14
            MouseArea {
                id: sessionArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.sessionIndex = (root.sessionIndex + 1) % sessionModel.rowCount()
                    password.forceActiveFocus()
                }
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        spacing: 20
        Repeater {
            model: [
                { glyph: "\u{f0709}", action: "suspend" },
                { glyph: "\u{f0450}", action: "reboot" },
                { glyph: "\u{f0425}", action: "powerOff" }
            ]
            Text {
                text: modelData.glyph
                color: powerArea.containsMouse ? "white" : Qt.rgba(1, 1, 1, 0.45)
                font.family: root.monoFont
                font.pixelSize: 20
                MouseArea {
                    id: powerArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sddm[modelData.action]()
                }
            }
        }
    }

    Component.onCompleted: password.forceActiveFocus()
}
