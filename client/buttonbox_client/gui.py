import platform
import sys
import webbrowser
from copy import deepcopy
from functools import partial
from subprocess import getoutput
from typing import TYPE_CHECKING, Any, Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QCloseEvent, QColor
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QLineEdit,
                             QMainWindow, QMessageBox, QWidget)
from serial.tools.list_ports import comports

try:
    from . import model
    from .icons import resource as _  # noqa
    from .ui.about_ui import Ui_About
    from .ui.licenses_ui import Ui_Licenses
    from .ui.profile_editor_ui import Ui_ProfileEditor
    from .ui.profiles_ui import Ui_Profiles
    from .ui.serial_monitor_ui import Ui_SerialMonitor
    from .ui.settings_ui import Ui_Settings
    from .ui.window_ui import Ui_MainWindow
except ImportError:
    import model  # type: ignore[no-redef]
    from icons import resource as _  # noqa
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
    import config  # type: ignore[no-redef]
    import version  # type: ignore[no-redef]
    config.init_config()

if TYPE_CHECKING:
    from .__main__ import Connection


def show_error(parent, title: str, desc: str) -> int:
    messagebox = QMessageBox(parent)
    messagebox.setIcon(QMessageBox.Icon.Critical)
    messagebox.setWindowTitle(title)
    messagebox.setText(desc)
    messagebox.setStandardButtons(QMessageBox.StandardButton.Ok)
    messagebox.setDefaultButton(QMessageBox.StandardButton.Ok)
    return messagebox.exec()


class Window(QMainWindow, Ui_MainWindow):  # type: ignore[misc]
    def __init__(self, conn: "Connection") -> None:
        super().__init__(None)
        self.conn = conn
        self.main_widget_detected = False
        self.profiles = model.sort_dict(model.load_profiles())
        self.current_profile: Optional[model.Profile] = None
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
        self.apply_dark()

        self.updateMainWidgetTimer = QTimer(self)
        self.updateMainWidgetTimer.timeout.connect(self.updateMainWidget)
        self.updateMainWidgetTimer.start(1000)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.populate_port_combo(select_default=True)
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
        prev_items = [
            self.profileCombo.itemText(i) for i in range(
                self.profileCombo.count()
            )
        ]
        new_items = ["None"] + [
            profile.name for profile in self.profiles.values()
        ]
        if prev_items == new_items:
            return  # Nothing changed
        prev_text = self.profileCombo.currentText()
        self.profileCombo.clear()
        for i, profile in enumerate(new_items):
            self.profileCombo.addItem(profile)
            if profile == prev_text or i == 0:
                self.profileCombo.setCurrentIndex(i)

    def populate_port_combo(self, select_default: bool = False) -> None:
        prev_items = [
            self.profileCombo.itemText(i) for i in range(
                self.profileCombo.count()
            )
        ]
        if prev_items == [i[0] for i in sorted(comports())]:
            return  # Nothing changed
        prev_text = self.profileCombo.currentText()
        self.profileCombo.clear()
        default_port = config.get_config_value("default_port")
        for i, port in enumerate(sorted(comports())):
            self.profileCombo.addItem(port[0])
            if (port[0] == default_port or i == 0) and select_default:
                # If default is not in list, fallback to index 0
                self.profileCombo.setCurrentIndex(i)
            elif port[0] == prev_text and not select_default:
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
        if self.profileCombo.count() < 1:
            return
        text = self.profileCombo.currentText()
        if self.main_widget_detected:
            self.set_profile(text)
        else:
            self.set_port(text)

    def set_profile(self, text: str) -> None:
        profile = None
        for prof in self.profiles.values():
            if prof.name == text:
                profile = prof
        if not profile:
            config.log(
                f"set_profile() called with nonexistent profile {text}",
                "ERROR",
            )
            show_error(
                self,
                "Invalid Profile",
                f"The Profile {text} doesn't exist.",
            )
            return
        self.current_profile = profile

    def test_check_box_changed(self) -> None:
        value = self.testCheckBox.isChecked()
        if value == self.conn.test_mode:
            return
        if value:
            self.conn.test_mode = True
            self.testModeFrame.setEnabled(True)
        else:
            self.conn.test_mode = False
            if self.conn.connected and self.conn.ser:
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
        self.actionProfiles.triggered.connect(self.open_profiles)
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

    def open_profiles(self) -> None:
        dialog = ProfilesDialog(self, self.profiles.copy())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.profiles = dialog.profiles
            model.save_profiles(self.profiles)

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
    def __init__(
        self,
        parent: QWidget,
        profiles: dict[int, model.Profile],
    ) -> None:
        super().__init__(parent)
        self.profiles = profiles
        self.setupUi(self)
        self.connectSignalsSlots()

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.updateUi()

    def updateUi(self) -> None:
        self.profiles = model.sort_dict(
            self.profiles
        )
        self.profilesList.clear()
        for profile in self.profiles.values():
            self.profilesList.addItem(profile.name)

    def connectSignalsSlots(self) -> None:
        self.addProfile.clicked.connect(self.new_profile)
        self.editProfile.clicked.connect(self.profile_editor)
        self.deleteProfile.clicked.connect(self.delete_profile)

    def new_profile(self) -> None:
        self.profiles[len(self.profiles)] = model.Profile.empty()
        self.updateUi()

    def delete_profile(self) -> None:
        try:
            selected = self.profilesList.selectedIndexes()[0].row()
        except IndexError:
            return
        self.profiles.pop(selected)
        self.profiles = model.rebuild_numbered_dict(self.profiles)
        self.updateUi()

    def profile_editor(self) -> None:
        try:
            selected = self.profilesList.selectedIndexes()[0].row()
        except IndexError:
            return
        dialog = ProfileEditor(self, deepcopy(self.profiles[selected]))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_profile = dialog.profile
            self.profiles[selected] = edited_profile
            self.updateUi()


class ProfileEditor(QDialog, Ui_ProfileEditor):  # type: ignore[misc]
    def __init__(self, parent: QWidget, profile: model.Profile) -> None:
        super().__init__(parent)
        self.profile = profile
        self.selected_matrix_point = (0, 0)
        self.setupUi(self)
        self.connectSignalsSlots()

    def _set_type_input_pair(
        self,
        type_combo: QComboBox,
        input_line: QLineEdit,
        input_combo: QComboBox,
    ) -> None:
        input_line.setEnabled(True)
        input_combo.setEnabled(True)
        if type_combo.currentText() == "Off":
            input_line.setEnabled(False)
            input_line.setText("")
            input_combo.setEnabled(False)
            input_combo.clear()
        elif type_combo.currentText() == "Command":
            input_line.setMaximumWidth(1000)
            input_combo.setMaximumWidth(0)
            input_combo.clear()
        elif type_combo.currentText() == "Game Action":
            input_line.setMaximumWidth(0)
            input_line.setText("")
            input_combo.setMaximumWidth(1000)
            if input_combo.count() < 1:
                self._populate_combo(input_combo)

    def _populate_combo(
        self,
        combo: QComboBox,
        selected: Optional[model.GAME_ACTION_ENTRY] = None,
    ) -> None:
        combo.clear()
        for i, action in enumerate(model.GAME_ACTIONS):
            action_class = model.find_class(action)
            combo.addItem(
                f"{action_class.game_name}: "  # type: ignore[union-attr]
                f"{action_class.name_for_action(action)}"  # type: ignore[union-attr]  # noqa
            )
            if (
                (
                    selected and
                    model.reverse_lookup(
                        model.GAME_LOOKUP, model.find_class(action)
                    ) == selected["game"]
                    and action.__name__ == selected["action"]
                )
                or i == 0
            ):
                combo.setCurrentIndex(i)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)

        # Name
        self.nameEdit.setText(self.profile.name)

        # Auto activate
        self.autoActivateCombo.clear()
        for i, item in enumerate(["Off"] + list(model.GAME_LOOKUP.keys())):
            self.autoActivateCombo.addItem(item)
            if self.profile.auto_activate == item:
                self.autoActivateCombo.setCurrentIndex(i)

        # LED profile
        self.ledCombo.clear()
        for i, item in enumerate(["Off"] + list(model.GAME_LOOKUP.keys())):
            self.ledCombo.addItem(item)
            if self.profile.led_profile == item:
                self.ledCombo.setCurrentIndex(i)

        # Single button
        if (type := self.profile.button_single["type"]) is None:
            self.singleTypeCombo.setCurrentText("Off")
        elif type == "command":
            self.singleTypeCombo.setCurrentText("Command")
            self.singleEdit.setText(self.profile.button_single["value"])
        else:
            self.singleTypeCombo.setCurrentText("Game Action")
            self._populate_combo(
                self.singleCombo,
                self.profile.button_single["value"],  # type: ignore[arg-type]
            )
        self._set_type_input_pair(
            self.singleTypeCombo, self.singleEdit, self.singleCombo
        )

    def connectSignalsSlots(self) -> None:
        self.nameEdit.textChanged.connect(self.name_changed)
        self.autoActivateCombo.currentTextChanged.connect(
            self.auto_activate_changed
        )
        self.ledCombo.currentTextChanged.connect(self.led_changed)
        self.singleTypeCombo.currentTextChanged.connect(self.single_changed)
        self.singleCombo.currentIndexChanged.connect(self.single_changed)
        self.singleEdit.textChanged.connect(self.single_changed)
        self.matrixTable.itemSelectionChanged.connect(self.matrix_selection)
        self.matrixTypeCombo.currentTextChanged.connect(self.matrix_changed)
        self.matrixCombo.currentIndexChanged.connect(self.matrix_changed)
        self.matrixEdit.textChanged.connect(self.matrix_changed)

    def name_changed(self) -> None:
        self.profile.name = self.nameEdit.text()

    def auto_activate_changed(self) -> None:
        new: Optional[str] = self.autoActivateCombo.currentText()
        if new == "Off":
            new = None
        self.profile.auto_activate = new

    def led_changed(self) -> None:
        new: Optional[str] = self.ledCombo.currentText()
        if new == "Off":
            new = None
        self.profile.led_profile = new

    def single_changed(self) -> None:
        if self.singleTypeCombo.currentText() == "Off":
            self.profile.button_single["type"] = None
            self.profile.button_single["value"] = None
        elif self.singleTypeCombo.currentText() == "Command":
            command = self.singleEdit.text()
            self.profile.button_single["type"] = "command"
            self.profile.button_single["value"] = command
        else:
            action_index = self.singleCombo.currentIndex()
            action = model.GAME_ACTIONS[action_index]
            game_class = model.find_class(action)
            self.profile.button_single["type"] = "game_action"
            self.profile.button_single["value"] = {
                "game": model.reverse_lookup(model.GAME_LOOKUP, game_class),
                "action": action.__name__,
            }
        self._set_type_input_pair(
            self.singleTypeCombo, self.singleEdit, self.singleCombo
        )

    def matrix_selection(self) -> None:
        try:
            index = self.matrixTable.selectedIndexes()[0]
        except KeyError:
            return
        self.selected_matrix_point = (index.column(), index.row())
        self.matrixTypeCombo.setEnabled(True)
        if (
            type := self.profile.get_button_matrix_entry_for(
                *self.selected_matrix_point
            )["type"]
        ) is None:
            self.matrixTypeCombo.setCurrentText("Off")
        elif type == "command":
            self.matrixTypeCombo.setCurrentText("Command")
            self.matrixEdit.setText(
                self.profile.get_button_matrix_entry_for(
                    *self.selected_matrix_point
                )["value"]
            )
        else:
            self.matrixTypeCombo.setCurrentText("Game Action")
            self._populate_combo(
                self.matrixCombo,
                self.profile.get_button_matrix_entry_for(  # type: ignore[arg-type]  # noqa
                    *self.selected_matrix_point
                )["value"],
            )
        self._set_type_input_pair(
            self.matrixTypeCombo,
            self.matrixEdit,
            self.matrixCombo,
        )

    def matrix_changed(self) -> None:
        if self.matrixTypeCombo.currentText() == "Off":
            self.profile.set_button_matrix_entry_for(
                *self.selected_matrix_point,
                {
                    "type": None,
                    "value": None,
                }
            )
        elif self.matrixTypeCombo.currentText() == "Command":
            command = self.matrixEdit.text()
            if command:
                self.profile.set_button_matrix_entry_for(
                    *self.selected_matrix_point,
                    {
                        "type": "command",
                        "value": command,
                    }
                )
        else:
            action_index = self.matrixCombo.currentIndex()
            action = model.GAME_ACTIONS[action_index]
            game_class = model.find_class(action)
            game_name = model.reverse_lookup(model.GAME_LOOKUP, game_class)
            self.profile.set_button_matrix_entry_for(
                *self.selected_matrix_point,
                {
                    "type": "game_action",
                    "value": {
                        "game": game_name,
                        "action": action.__name__,
                    },
                }
            )
        self._set_type_input_pair(
            self.matrixTypeCombo,
            self.matrixEdit,
            self.matrixCombo,
        )


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
