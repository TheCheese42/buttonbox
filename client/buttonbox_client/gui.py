import platform
import sys
import webbrowser
from functools import partial
# XXX from pathlib import Path
from subprocess import getoutput

from PyQt6.QtGui import QAction, QActionEvent
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow
from serial.tools.list_ports import comports

try:
    from .ui.about_ui import Ui_About
    from .ui.licenses_ui import Ui_Licenses
    from .ui.profile_editor_ui import Ui_ProfileEditor
    from .ui.profiles_ui import Ui_Profiles
    from .ui.serial_monitor_ui import Ui_SerialMonitor
    from .ui.settings_ui import Ui_Settings
    from .ui.window_ui import Ui_MainWindow
except ImportError:
    from ui.about_ui import Ui_About
    from ui.licenses_ui import Ui_Licenses
    from ui.profile_editor_ui import Ui_ProfileEditor
    from ui.profiles_ui import Ui_Profiles
    from ui.serial_monitor_ui import Ui_SerialMonitor
    from ui.settings_ui import Ui_Settings
    from ui.window_ui import Ui_MainWindow

try:
    from . import config, version
    config.init_config()
except ImportError:
    import config
    import version
    config.init_config()


# XXX ICONS_PATH = Path(__file__).parent / "icons"


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, conn):
        super().__init__(None)
        self.conn = conn
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

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.setMinimumSize(self.size())
        self.refreshPorts()

    def refreshPorts(self):
        self.menuPort.clear()
        for port in sorted(comports()):
            action = QAction(port[0])
            self.menuPort.addAction(action)
            action.setCheckable(True)
            action.changed.connect(partial(self.port_selected, action))

    def select_default_port(self):
        if port := config.get_config_value("default_port"):
            for action in self.menuPort.actions():
                if action.text() == port:
                    action.activate(QAction.ActionEvent.Trigger)
                    break

    def port_selected(self, selected_action: QAction):
        # selected_action is provided by partial
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

    def connectSignalsSlots(self):
        self.actionSettings.triggered.connect(self.settings)
        self.actionProfiles.triggered.connect(self.profiles)
        self.actionSerial_Monitor.triggered.connect(self.serial_monitor)
        self.actionLog.triggered.connect(self.open_log)
        self.actionMicrocontroller_Debug_Log.triggered.connect(
            self.mcdebug_log
        )
        self.actionAbout.triggered.connect(self.about)
        self.actionOpen_GitHub.triggered.connect(self.open_github)
        self.actionOpen_Source_Licenses.triggered.connect(self.licenses)
        self.actionDark_Mode.changed.connect(self.dark_mode)

    def dark_mode(self):
        dark = self.actionDark_Mode.isChecked()
        config.set_config_value("dark", dark)
        self.apply_dark()

    def apply_dark(self):
        dark = config.get_config_value("dark")
        self.setStyleSheet(
            self.dark_stylesheet if dark else self.light_stylesheet
        )

    def about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def licenses(self):
        dialog = LicensesDialog(self)
        dialog.exec()

    def profiles(self):
        dialog = ProfilesDialog(self)
        dialog.exec()

    def serial_monitor(self):
        dialog = SerialMonitor(self)
        dialog.exec()

    def settings(self):
        dialog = Settings(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_port = dialog.portBox.currentText()
            config.set_config_value("default_port", selected_port)
            self.select_default_port()

    def open_github(self):
        try:
            webbrowser.WindowsDefault().open(
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

    def open_log(self):
        try:
            webbrowser.WindowsDefault().open(str(config.LOGGER_PATH))
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(f"start {config.LOGGER_PATH}")
            else:
                getoutput(f"open {config.LOGGER_PATH}")

    def mcdebug_log(self):
        try:
            webbrowser.WindowsDefault().open(str(config.MC_DEBUG_LOG_PATH))
        except Exception:
            system = platform.system()
            if system == "Windows":
                getoutput(f"start {config.MC_DEBUG_LOG_PATH}")
            else:
                getoutput(f"open {config.MC_DEBUG_LOG_PATH}")


class LicensesDialog(QDialog, Ui_Licenses):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)


class AboutDialog(QDialog, Ui_About):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.version.setText(version.version_string)


class ProfilesDialog(QDialog, Ui_Profiles):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)

    def profile_editor(self):
        dialog = ProfileEditor(self)
        dialog.exec()


class ProfileEditor(QDialog, Ui_ProfileEditor):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)


class SerialMonitor(QDialog, Ui_SerialMonitor):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)


class Settings(QDialog, Ui_Settings):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def setupUi(self, *args, **kwargs):
        super().setupUi(*args, **kwargs)
        self.portBox.clear()
        prev_default = config.get_config_value("default_port")
        cur_index = 0
        for i, port in enumerate(sorted(comports())):
            self.portBox.addItem(port[0])
            if port[0] == prev_default:
                cur_index = i
        self.portBox.setCurrentIndex(cur_index)


def main(conn):
    app = QApplication(sys.argv)
    app.setApplicationName("Buttonbox Client")
    app.setApplicationDisplayName("Buttonbox Client")
    app.setApplicationVersion(version.version_string)
    win = Window(conn)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
