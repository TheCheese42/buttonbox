import platform
import sys
import webbrowser
from functools import partial
from subprocess import getoutput
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QCloseEvent, QColor
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QWidget
from serial.tools.list_ports import comports

try:
    from .icons import resource as _  # noqa
    from .ui.about_ui import Ui_About
    from .ui.licenses_ui import Ui_Licenses
    from .ui.profile_editor_ui import Ui_ProfileEditor
    from .ui.profiles_ui import Ui_Profiles
    from .ui.serial_monitor_ui import Ui_SerialMonitor
    from .ui.settings_ui import Ui_Settings
    from .ui.window_ui import Ui_MainWindow
except ImportError:
    from icons import resource as _  # noqa
    from ui.about_ui import Ui_About
    from ui.licenses_ui import Ui_Licenses
    from ui.profile_editor_ui import Ui_ProfileEditor
    from ui.profiles_ui import Ui_Profiles
    from ui.serial_monitor_ui import Ui_SerialMonitor
    from ui.settings_ui import Ui_Settings
    from ui.window_ui import Ui_MainWindow

try:
    if TYPE_CHECKING:
        from .__main__ import Connection
    from . import config, version
    config.init_config()
except ImportError:
    if TYPE_CHECKING:
        from __main__ import Connection  # type: ignore[no-redef]
    import config  # type: ignore[no-redef]
    import version  # type: ignore[no-redef]
    config.init_config()


class Window(QMainWindow, Ui_MainWindow):  # type: ignore[misc]
    def __init__(self, conn: "Connection") -> None:
        super().__init__(None)
        self.conn = conn
        self.main_widget_detected = False
        self.setupUi(self)
        self.select_default_port()

        self.connectSignalsSlots()
        self.light_stylesheet = self.styleSheet()
        self.dark_stylesheet = """
            QWidget {
                background-color: rgb(50, 50, 50);
                color: white;
                selection-background-color: transparent;
            }
            QPlainTextEdit {
                background-color: rgb(60, 60, 60);
            }
            QMenu {
                background-color: rgb(60, 60, 60);
            }
            QMenuBar {
                background-color: rgb(55, 55, 55);
            }
            QMenu:hover {
                background-color: rgb(55, 55, 55);
            }
            QMenu:pressed {
                background-color: rgb(65, 65, 65);
            }
            QCheckbox::indicator:hover {
                background-color: rgb(75, 75, 75);
            }
            QCheckbox::indicator:pressed {
                background-color: rgb(80, 80, 80);
            }
            QComboBox {
                background-color: rgb(60, 60, 60);
            }
            QComboBox:selected {
                background-color: rgb(40, 40, 40);
            }
        """
        print(self.styleSheet())
        self.apply_dark()

        self.updateMainWidgetTimer = QTimer(self)
        self.updateMainWidgetTimer.timeout.connect(self.updateMainWidget)
        self.updateMainWidgetTimer.start(1000)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.setMinimumSize(self.size())
        self.refreshPorts()
        self.updateMainWidget()

    def updateMainWidget(self) -> None:
        if self.conn.handshaked:
            self.main_widget_detected = True
            self.statusLabel.setText("Detected")
            self.statusLabel.palette().windowText().setColor(
                QColor.fromRgb(50, 180, 10)
            )
            self.profileLabel.setText("Profile:")
            self.profileCombo.setPlaceholderText("Select Profile")
            self.populate_profile_combo()
            self.testCheckBox.setEnabled(True)
        else:
            self.main_widget_detected = False
            self.statusLabel.setText("Undetected")
            self.statusLabel.palette().windowText().setColor(
                QColor.fromRgb(240, 50, 30)
            )
            self.profileLabel.setText("Port:")
            self.profileCombo.setPlaceholderText("Select Port")
            self.populate_port_combo()
            self.testCheckBox.setEnabled(False)
            self.testCheckBox.setChecked(False)
        self.test_check_box_changed()

    def populate_profile_combo(self) -> None:
        self.profileCombo.clear()  # TODO

    def populate_port_combo(self) -> None:
        self.profileCombo.clear()
        default_port = config.get_config_value("default_port")
        for i, port in enumerate(sorted(comports())):
            self.profileCombo.addItem(port[0])
            if port[0] == default_port or i == 0:
                # If default is not in list, fallback to index 0
                self.profileCombo.setCurrentIndex(i)

    def refreshPorts(self) -> None:
        prev_selected = self.menuPort.activeAction()
        self.menuPort.clear()
        if not self.main_widget_detected:
            self.populate_port_combo()
        for port in sorted(comports()):
            action = QAction(port[0])
            self.menuPort.addAction(action)
            action.setCheckable(True)
            if prev_selected and prev_selected.text() == port[0]:
                action.activate(QAction.ActionEvent.Trigger)
            action.changed.connect(partial(self.port_selected, action))

    def select_default_port(self) -> None:
        if port := config.get_config_value("default_port"):
            for action in self.menuPort.actions():
                if action.text() == port:
                    action.activate(QAction.ActionEvent.Trigger)
                    break

    def port_selected(self, selected_action: QAction) -> None:
        # selected_action is provided by partial
        self.set_port(selected_action.text())
        checked = False
        for action in self.menuPort.actions():
            if action == selected_action:
                if action.isChecked():
                    checked = True
                else:
                    checked = False
        if checked:
            for action in self.menuPort.actions():
                if action != selected_action:
                    action.setChecked(False)

    def set_port(self, port: str) -> None:
        self.conn.port = port
        self.conn.reconnect()

        if not self.main_widget_detected:
            for i, action in enumerate(self.profileCombo.actions()):
                if action.text() == port:
                    self.profileCombo.setCurrentIndex(i)

    def profile_port_box_changed(self) -> None:
        text = self.profileCombo.currentText()
        if self.main_widget_detected:
            self.set_profile(text)  # TODO
        else:
            self.set_port(text)

    def test_check_box_changed(self) -> None:
        value = self.testCheckBox.isChecked()
        if value == self.conn.test_mode:
            return
        if value:
            self.conn.test_mode = True
            self.testModeFrame.setEnabled(True)
        else:
            self.conn.test_mode = False
            if self.conn.connected:
                self.conn.ser.read_all()
            self.conn.write_queue.clear()
            self.testModeFrame.setEnabled(False)

    def connectSignalsSlots(self) -> None:
        self.profileCombo.currentTextChanged.connect(
            self.profile_port_box_changed
        )
        self.testCheckBox.stateChanged.connect(self.test_check_box_changed)

        self.actionRefresh_Ports.triggered.connect(self.refreshPorts)
        self.actionPause.triggered.connect(self.toggle_pause)
        self.actionRun_in_Background.triggered.connect(self.close)
        self.actionQuit.triggered.connect(self.full_quit)
        self.actionSettings.triggered.connect(self.settings)
        self.actionProfiles.triggered.connect(self.profiles)
        self.actionSerial_Monitor.triggered.connect(self.serial_monitor)
        self.actionLog.triggered.connect(self.open_log)
        self.actionMicrocontroller_Debug_Log.triggered.connect(
            self.mcdebug_log
        )
        self.actionExport_Serial_History.triggered.connect(
            self.export_open_serial_history
        )
        self.actionAbout.triggered.connect(self.about)
        self.actionOpen_GitHub.triggered.connect(self.open_github)
        self.actionOpen_Source_Licenses.triggered.connect(self.licenses)
        self.actionDark_Mode.changed.connect(self.dark_mode)

    def toggle_pause(self) -> None:
        paused = self.actionPause.isChecked()
        self.conn.paused = paused

    def dark_mode(self) -> None:
        dark = self.actionDark_Mode.isChecked()
        config.set_config_value("dark", dark)
        self.apply_dark()

    def apply_dark(self) -> None:
        dark = config.get_config_value("dark")
        self.setStyleSheet(
            self.dark_stylesheet if dark else self.light_stylesheet
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        event.ignore()
        self.close()

    def close(self) -> bool:
        self.hide()
        return False

    def full_quit(self) -> None:
        self.conn.close()
        super().close()
        sys.exit(0)

    def about(self) -> None:
        dialog = AboutDialog(self)
        dialog.exec()

    def licenses(self) -> None:
        dialog = LicensesDialog(self)
        dialog.exec()

    def profiles(self) -> None:
        dialog = ProfilesDialog(self)
        dialog.exec()

    def serial_monitor(self) -> None:
        dialog = SerialMonitor(self, self.conn)
        dialog.exec()

    def settings(self) -> None:
        dialog = Settings(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_port = dialog.portBox.currentText()
            config.set_config_value("default_port", selected_port)
            self.select_default_port()
            selected_baudrate = dialog.baudrateSpin.value()
            config.set_config_value("baudrate", selected_baudrate)
            self.conn.port = selected_port
            self.conn.baudrate = selected_baudrate
            self.conn.reconnect()

    def open_github(self) -> None:
        try:
            webbrowser.WindowsDefault().open(  # type: ignore[attr-defined]  # noqa
                "https://github.com/asunadawg/buttonbox"
            )
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(
                    "start https://github.com/asunadawg/buttonbox"
                )
            else:
                getoutput(
                    "open https://github.com/asunadawg/buttonbox"
                )

    def open_log(self) -> None:
        try:
            webbrowser.WindowsDefault().open(str(config.LOGGER_PATH))  # type: ignore[attr-defined]  # noqa
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(f"start {config.LOGGER_PATH}")
            else:
                getoutput(f"open {config.LOGGER_PATH}")

    def export_open_serial_history(self) -> None:
        with open(config.SER_HISTORY_PATH, "w", encoding="utf-8") as fp:
            fp.writelines(self.conn.full_history)

        try:
            webbrowser.WindowsDefault().open(str(config.SER_HISTORY_PATH))  # type: ignore[attr-defined]  # noqa
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(f"start {config.SER_HISTORY_PATH}")
            else:
                getoutput(f"open {config.SER_HISTORY_PATH}")

    def mcdebug_log(self) -> None:
        try:
            webbrowser.WindowsDefault().open(str(config.MC_DEBUG_LOG_PATH))  # type: ignore[attr-defined]  # noqa
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(f"start {config.MC_DEBUG_LOG_PATH}")
            else:
                getoutput(f"open {config.MC_DEBUG_LOG_PATH}")


class LicensesDialog(QDialog, Ui_Licenses):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)


class AboutDialog(QDialog, Ui_About):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.version.setText(version.version_string)


class ProfilesDialog(QDialog, Ui_Profiles):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)

    def profile_editor(self) -> None:
        dialog = ProfileEditor(self)
        dialog.exec()


class ProfileEditor(QDialog, Ui_ProfileEditor):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)


class SerialMonitor(QDialog, Ui_SerialMonitor):  # type: ignore[misc]
    def __init__(self, parent: QWidget, conn: "Connection"):
        super().__init__(parent)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.conn = conn
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(50)
        self.from_index = 0

    def connectSignalsSlots(self) -> None:
        self.enterBtn.clicked.connect(self.enter)
        self.clearBtn.clicked.connect(self.clear)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.monitorText.clear()

    def refresh(self) -> None:
        self.monitorText.clear()
        history = self.conn.in_history.copy()
        history.append("")
        self.monitorText.setPlainText("\n".join(history[self.from_index:]))

    def enter(self) -> None:
        cmd = self.cmdEdit.text()
        if cmd:
            self.conn.write_queue.append(cmd)

    def clear(self) -> None:
        self.from_index = len(self.conn.in_history)
        self.refresh()


class Settings(QDialog, Ui_Settings):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.portBox.clear()
        prev_default = config.get_config_value("default_port")
        cur_index = 0
        for i, port in enumerate(sorted(comports())):
            self.portBox.addItem(port[0])
            if port[0] == prev_default:
                cur_index = i
        self.portBox.setCurrentIndex(cur_index)

        self.baudrateSpin.setValue(config.get_config_value("baudrate"))


def launch_gui(conn: "Connection") -> tuple[QApplication, Window]:
    app = QApplication(sys.argv)
    app.setApplicationName("Buttonbox Client")
    app.setApplicationDisplayName("Buttonbox Client")
    app.setApplicationVersion(version.version_string)
    win = Window(conn)
    win.show()
    return app, win


if __name__ == "__main__":
    print("This must be run by the background process in __main__.py")
    sys.exit(1)
