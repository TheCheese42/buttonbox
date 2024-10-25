import platform
import string
import sys
import webbrowser
from copy import deepcopy
from itertools import zip_longest
from pathlib import Path
from subprocess import getoutput
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

from pynput.keyboard import Key
from PyQt6.QtCore import QModelIndex, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
                             QKeySequenceEdit, QLabel, QLineEdit,
                             QListWidgetItem, QMainWindow, QMessageBox,
                             QWidget)
from serial import SerialException
from serial.tools.list_ports import comports

try:
    from . import model
    from .icons import resource as _  # noqa
    from .ui.about_ui import Ui_About
    from .ui.custom_actions_ui import Ui_CustomActionsManager
    from .ui.edit_macro_action_ui import Ui_EditAction
    from .ui.keyboard_ui import Ui_KeyboardShortcuts
    from .ui.licenses_ui import Ui_Licenses
    from .ui.macro_editor_ui import Ui_MacroEditor
    from .ui.profile_editor_ui import Ui_ProfileEditor
    from .ui.profiles_ui import Ui_Profiles
    from .ui.serial_monitor_ui import Ui_SerialMonitor
    from .ui.settings_ui import Ui_Settings
    from .ui.window_ui import Ui_MainWindow
except ImportError:
    import model  # type: ignore[no-redef]
    from icons import resource as _  # noqa
    from ui.about_ui import Ui_About
    from ui.custom_actions_ui import Ui_CustomActionsManager
    from ui.edit_macro_action_ui import Ui_EditAction
    from ui.keyboard_ui import Ui_KeyboardShortcuts
    from ui.licenses_ui import Ui_Licenses
    from ui.macro_editor_ui import Ui_MacroEditor
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


def show_error(parent: QWidget, title: str, desc: str) -> int:
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
        self.controller = model.start_controller()
        self.main_widget_detected = False
        self.macros = config.get_macros()
        self.profiles = model.sort_dict(model.load_profiles())
        self.current_profile: Optional[model.Profile] = None
        self.test_mode = False
        self.test_profile = model.TestProfile()
        self.games_instances = {}
        for game in model.GAME_LOOKUP.values():
            if game == model.TestGame:
                self.games_instances[game] = game(self.conn, self)
            else:
                self.games_instances[game] = game(self.conn, self.controller)
        for action, name in config.get_custom_actions().items():
            model.Custom.add_action(action, name)
        model.register_custom_shortcut_actions()
        model.populate_game_actions()
        self.games_instances[model.Custom].register_lambdas()  # type: ignore[attr-defined]  # noqa
        self.conn.rotary_encoder_clockwise = self._rot_clockwise
        self.conn.rotary_encoder_counterclockwise = self._rot_counterclockwise
        self.conn.status_button_matrix = self._button_matrix
        self.conn.status_button_single = self._button_single
        self.conn.mc_debug = self._mc_debug
        self.conn.mc_warning = self._mc_warning
        self.conn.mc_error = self._mc_error
        self.conn.mc_critical = self._mc_critical
        self.setupUi(self)

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

        self.detectProfileTimer = QTimer(self)
        self.detectProfileTimer.timeout.connect(self.detect_profiles)
        self.detectProfileTimer.start(1000)

        self.ledManagerTimer = QTimer(self)
        self.ledManagerTimer.timeout.connect(self.call_led_manager)
        self.ledManagerTimer.start(100)

        if config.get_config_value("hide_to_tray"):
            QTimer.singleShot(500, self.hide)

    def detect_profiles(self) -> None:
        if not config.get_config_value("auto_detect_profiles"):
            return
        for profile in self.profiles.values():
            detect_method = profile.auto_activate_method()
            if not detect_method:
                continue
            game: Optional[type[model.Game]] = model.find_class(detect_method)
            if game is None:
                config.log(
                    "Can't find class of detection method "
                    f"{detect_method.__name__}", "ERROR",
                )
                continue
            if self.current_profile is None:
                if detect_method(game):
                    self.set_profile(profile.name)
                continue
            cur_detect_method = self.current_profile.auto_activate_method()
            if not cur_detect_method:
                cur_priority = 1
            else:
                cur_game: Optional[type[model.Game]] = model.find_class(
                    cur_detect_method
                )
                if cur_game is None:
                    config.log(
                        "Can't find class of detection method "
                        f"{cur_detect_method.__name__}", "ERROR",
                    )
                    return
                cur_priority = cur_game.priority
            if game.priority > cur_priority:
                if detect_method(self.games_instances[game]):
                    self.set_profile(profile.name)

    def call_led_manager(self) -> None:
        if not self.current_profile:
            return
        led_manager = self.current_profile.led_manager_method()
        if not led_manager:
            return
        game: Optional[type[model.Game]] = model.find_class(led_manager)
        if game is None:
            config.log(
                "Can't find class of detection method "
                f"{led_manager.__name__}", "ERROR",
            )
            return
        led_manager(self.games_instances[game])

    def _rot_clockwise(self) -> None:
        if self.test_mode:
            if self.dial.value() >= self.dial.maximum():
                self.dial.setValue(self.dial.minimum())
            else:
                self.dial.setValue(self.dial.value() + 1)
        else:
            config.log("Issuing Volume Up", "DEBUG")
            self.controller.tap(Key.media_volume_up)

    def _rot_counterclockwise(self) -> None:
        if self.test_mode:
            if self.dial.value() <= self.dial.minimum():
                self.dial.setValue(self.dial.maximum())
            else:
                self.dial.setValue(self.dial.value() - 1)
        else:
            config.log("Issuing Volume Down", "DEBUG")
            self.controller.tap(Key.media_volume_down)

    def _button_single(self, state: int) -> None:
        if not self.current_profile:
            return
        model.exec_entry(
            self.current_profile.button_single,
            bool(state),
            self.games_instances,
        )

    def _button_matrix(self, matrix: list[list[int]]) -> None:
        if not self.current_profile:
            return
        for i, row in enumerate(matrix):
            for j, state in enumerate(row):
                entry = self.current_profile.get_button_matrix_entry_for(i, j)
                model.exec_entry(entry, bool(state), self.games_instances)

    def _mc_debug(self, msg: str) -> None:
        config.log_mc(f"[DEBUG] {msg}")

    def _mc_warning(self, msg: str) -> None:
        config.log_mc(f"[WARNING] {msg}")

    def _mc_error(self, msg: str) -> None:
        config.log_mc(f"[ERROR] {msg}")

    def _mc_critical(self, msg: str) -> None:
        config.log_mc(f"[CRITICAL] {msg}")

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.populate_port_combo(select_default=True)
        self.setMinimumSize(self.size())
        self.refreshPorts()
        self.updateMainWidget()
        self.testModeFrame.setDisabled(True)

    def updateMainWidget(self) -> None:
        if self.conn.handshaked:
            self.main_widget_detected = True
            self.statusLabel.setText("Detected")
            self.statusLabel.setStyleSheet(
                "QLabel { color: rgb(50, 180, 10); }"
            )
            self.profileLabel.setText("Profile:")
            self.profileCombo.setPlaceholderText("Select Profile")
            self.populate_profile_combo()
            self.testCheckBox.setEnabled(True)
        else:
            self.main_widget_detected = False
            self.statusLabel.setText("Undetected")
            self.statusLabel.setStyleSheet(
                "QLabel { color: rgb(240, 50, 30); }"
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
        if not self.main_widget_detected:
            self.populate_port_combo()

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
        if text == "test":
            self.current_profile = self.test_profile
            return
        if text.lower() == "none":
            self.current_profile = None
            if self.main_widget_detected:
                # 0 is "None"
                self.profileCombo.setCurrentIndex(0)
            return
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
        if self.main_widget_detected:
            self.profileCombo.setCurrentText(profile.name)

    def test_check_box_changed(self) -> None:
        value = self.testCheckBox.isChecked()
        self.profileCombo.setDisabled(value)
        if value == self.test_mode:
            return
        if value:
            self.test_mode = True
            self.testModeFrame.setEnabled(True)
            self.set_profile("test")
        else:
            self.test_mode = False
            if self.conn.connected and self.conn.ser:
                try:
                    self.conn.ser.read_all()
                except SerialException:
                    pass
            self.conn.write_queue.clear()
            self.testModeFrame.setEnabled(False)
            self.current_profile = None

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
        self.actionKeyboard_Shortcuts.triggered.connect(
            self.keyboard_shortcuts
        )
        self.actionManage_Custom_Actions.triggered.connect(
            self.manage_custom_actions
        )
        self.actionManage_Macros.triggered.connect(self.macro_editor)
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
        super().close()
        instance = QApplication.instance()
        if instance is None:
            self.conn.close()
            sys.exit(0)
        else:
            instance.quit()

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
            selected_baudrate = dialog.baudrateSpin.value()
            config.set_config_value("baudrate", selected_baudrate)
            self.conn.port = selected_port
            self.conn.baudrate = selected_baudrate
            auto_detect_profiles = dialog.autoDetectCheck.isChecked()
            config.set_config_value(
                "auto_detect_profiles", auto_detect_profiles
            )
            hide_to_tray = dialog.hideToTrayCheck.isChecked()
            config.set_config_value(
                "hide_to_tray", hide_to_tray
            )
            self.conn.reconnect()

    def keyboard_shortcuts(self) -> None:
        dialog = KeyboardShortcuts(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for entry in dialog.items:
                game = entry[0]
                action = entry[1]
                edit = entry[2]
                shortcut = edit.keySequence().toString()
                try:
                    shortcut.encode("utf-8")
                except UnicodeEncodeError:
                    config.log("Invalid shortcut configured", "ERROR")
                    show_error(
                        self, "Invalid Character",
                        "You entered an invalid character in the shortcuts "
                        "menu. This commonly happens when using alternate "
                        "graphics (AltGr). Please do not use these characters."
                    )
                    continue
                config.set_keyboard_shortcut(game, action, shortcut)

    def macro_editor(self) -> None:
        dialog = MacroEditor(self, deepcopy(self.macros))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.macros = dialog.macros
            config.set_macros(self.macros)

    def manage_custom_actions(self) -> None:
        dialog = CustomActionsManager(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            list_items = [dialog.actionsList.item(i).text()
                          for i in range(dialog.actionsList.count())]
            for id, new_name in zip_longest(
                dialog.custom_actions.keys(), list_items
            ):
                if id is not None:
                    dialog.custom_actions[id] = new_name
                else:
                    dialog.custom_actions[
                        dialog.name_to_unique(new_name)
                    ] = new_name
            model.CUSTOM_ACTIONS = dialog.custom_actions
            config.set_custom_actions(model.CUSTOM_ACTIONS)
            model.register_custom_shortcut_actions()
            model.populate_game_actions()
            self.games_instances[model.Custom].register_lambdas()  # type: ignore[attr-defined]  # noqa

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
        self.textBrowser.clear()
        license_path = config.LICENSE_PATH
        if license_path.exists():
            text = license_path.read_text("utf-8")
        else:
            system = platform.system()
            path: Optional[Path] = None
            if system == "Windows":
                path = config.WINDOWS_LICENSE_PATH
            elif system == "Linux":
                path = config.LINUX_LICENSE_PATH
            if path and path.exists():
                text = path.read_text("utf-8")
            else:
                text = "Couldn't find Licenses File for your Platform. " \
                       "Please contact the publisher about it or browse " \
                       "The available Files on GitHub: " \
                       "https://github.com/asunadawg/buttonbox/tree/main/" \
                       "client/buttonbox_client/licenses"
        self.textBrowser.clear()
        self.textBrowser.setText(text)


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
        prev_text = combo.currentText()
        combo.clear()
        new_current = 0
        for i, action in enumerate(model.GAME_ACTIONS):
            action_class = model.find_class(action)
            text = (
                f"{action_class.game_name}: "  # type: ignore[union-attr]
                f"{action_class.name_for_action(action)}"  # type: ignore[union-attr]  # noqa
            )
            combo.addItem(text)
            if (
                (
                    selected and
                    model.reverse_lookup(
                        model.GAME_LOOKUP, model.find_class(action)
                    ) == selected["game"]
                    and action.__name__ == selected["action"]
                ) or text == prev_text
            ):
                new_current = i
        combo.setCurrentIndex(new_current)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)

        # Name
        self.nameEdit.setText(self.profile.name)

        # Auto activate
        self.autoActivateCombo.clear()
        # Need to keep track as index will decrease with every hidden item
        amount_hidden = 0
        for i, item in enumerate(["Off"] + list(model.GAME_LOOKUP.keys())):
            if (g := model.GAME_LOOKUP.get(item)) and g.hidden:
                # Filter hidden
                amount_hidden += 1
                continue
            if (
                (g := model.GAME_LOOKUP.get(item))
                and g.detect == model.Game.detect
            ):
                # Filter those that don't implement detect()
                amount_hidden += 1
                continue

            self.autoActivateCombo.addItem(item)
            if self.profile.auto_activate == item:
                self.autoActivateCombo.setCurrentIndex(i - amount_hidden)

        # LED profile
        self.ledCombo.clear()
        # Need to keep track as index will decrease with every hidden item
        amount_hidden = 0
        for i, item in enumerate(["Off"] + list(model.GAME_LOOKUP.keys())):
            if (g := model.GAME_LOOKUP.get(item)) and g.hidden:
                # Filter hidden
                amount_hidden += 1
                continue
            if (
                (g := model.GAME_LOOKUP.get(item))
                and g.led_manager == model.Game.led_manager
            ):
                # Filter those that don't implement led_manager()
                amount_hidden += 1
                continue

            self.ledCombo.addItem(item)
            if self.profile.led_profile == item:
                self.ledCombo.setCurrentIndex(i - amount_hidden)

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
        self.selected_matrix_point = (index.row(), index.column())
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
            # So we don't accidentally clear our combos using matrix_changed
            self.matrixTypeCombo.blockSignals(True)
            self.matrixCombo.blockSignals(True)
            self.matrixEdit.blockSignals(True)
            self.matrixTypeCombo.setCurrentText("Game Action")
            self._populate_combo(
                self.matrixCombo,
                self.profile.get_button_matrix_entry_for(  # type: ignore[arg-type]  # noqa
                    *self.selected_matrix_point
                )["value"],
            )
            self.matrixTypeCombo.blockSignals(False)
            self.matrixCombo.blockSignals(False)
            self.matrixEdit.blockSignals(False)
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
        self.timer.start(100)
        self.from_index = 0

    def connectSignalsSlots(self) -> None:
        self.enterBtn.clicked.connect(self.enter)
        self.clearBtn.clicked.connect(self.clear)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.monitorText.clear()

    def refresh(self) -> None:
        history = self.conn.in_history.copy()
        history.append("")
        # [:-1] to strip the last newline
        new_text = "".join(history[self.from_index:])[:-1]
        if self.monitorText.toPlainText() != new_text:
            self.monitorText.setPlainText(new_text)
            self.monitorText.verticalScrollBar().setValue(
                self.monitorText.verticalScrollBar().maximum()
            )

    def enter(self) -> None:
        cmd = self.cmdEdit.text()
        if cmd:
            self.conn.write_queue.append(cmd)
        self.cmdEdit.setText("")

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

        self.autoDetectCheck.setChecked(
            config.get_config_value("auto_detect_profiles")
        )

        self.hideToTrayCheck.setChecked(
            config.get_config_value("hide_to_tray")
        )


class KeyboardShortcuts(QDialog, Ui_KeyboardShortcuts):  # type: ignore[misc]
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        # Ex.: [("game1", "action1", QKeySequenceEdit()), ...]
        self.items: list[tuple[str, str, QKeySequenceEdit]] = []
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.items.clear()
        lo = self.shortcutsLayout
        for action in model.SHORTCUT_ACTIONS:
            game: Optional[type[model.Game]] = model.find_class(action)
            if game is None:
                config.log(
                    "Can't find class of action "
                    f"{action.__name__}", "ERROR",
                )
                show_error(
                    self,
                    "Invalid Action",
                    f"Can't find game for action {action.__name__}.",
                )
                self.reject()
                return
            game: type[model.Game]  # type: ignore[no-redef]
            game_str = model.reverse_lookup(model.GAME_LOOKUP, game)
            form = QFormLayout()
            label = QLabel()
            label.setText(f"{game.game_name}: {game.name_for_action(action)}")
            edit = QKeySequenceEdit()
            if (sc := config.get_keyboard_shortcut(game_str, action.__name__)):
                edit.setKeySequence(QKeySequence.fromString(sc))
            form.addRow(label, edit)
            self.items.append((game_str, action.__name__, edit))
            lo.addLayout(form)


class CustomActionsManager(QDialog, Ui_CustomActionsManager):  # type: ignore[misc]  # noqa
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.custom_actions = model.CUSTOM_ACTIONS.copy()
        self.setupUi(self)
        self.connectSignalsSlots()

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.actionsList.clear()
        for name in self.custom_actions.values():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.actionsList.addItem(item)

    def connectSignalsSlots(self) -> None:
        self.addButton.clicked.connect(self.add)
        self.removeButton.clicked.connect(self.remove)

    def add(self) -> None:
        item = QListWidgetItem("New Action")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.actionsList.addItem(item)

    def remove(self) -> None:
        try:
            item = self.actionsList.selectedItems()[0]
        except IndexError:
            return
        name = item.text()
        self.actionsList.takeItem(self.actionsList.indexFromItem(item).row())
        try:
            unique = model.reverse_lookup(self.custom_actions, name)
        except KeyError:
            return
        del self.custom_actions[unique]

    def name_to_unique(self, name: str) -> str:
        unique = "_" + name.lower().strip().replace(" ", "_")
        for char in unique:
            if char in unique:
                if char not in string.ascii_letters + string.digits + "_":
                    unique = unique.replace(char, "")

        if unique in self.custom_actions:
            n = 1
            while True:
                if unique + f"_{n}" in self.custom_actions:
                    n += 1
                else:
                    break
            unique += f"_{n}"
        return unique


class MacroEditor(QDialog, Ui_MacroEditor):  # type: ignore[misc]
    def __init__(self, parent: QWidget, macros: list[config.MACRO]) -> None:
        super().__init__(parent)
        self.macros = macros
        self.items_macros: list[tuple[QListWidgetItem, config.MACRO]] = []
        self.items_actions: list[
            tuple[QListWidgetItem, config.MACRO_ACTION]
        ] = []
        self.cur_macro: Optional[config.MACRO] = None
        self.setupUi(self)
        self.connectSignalsSlots()

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        self.updateUi()

    def updateUi(self) -> None:
        self.macroList.clear()
        for macro in self.macros:
            item = QListWidgetItem(macro["name"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.items_macros.append((item, macro))
            self.macroList.addItem(item)
        self.actionList.clear()

    def connectSignalsSlots(self) -> None:
        self.macroList.itemSelectionChanged.connect(self.macro_list_selection)
        self.macroList.itemChanged.connect(self.rename_macro)
        self.newMacroBtn.pressed.connect(self.new_macro)
        self.delMacroBtn.pressed.connect(self.del_macro)
        self.changeBtn.pressed.connect(self.change_action)
        self.deleteBtn.pressed.connect(self.delete_action)
        self.modeUntilReleasedRadio.pressed.connect(self.mode_until_released)
        self.modeUntilPressedRadio.pressed.connect(self.mode_until_pressed)
        self.modeNTimesRadio.pressed.connect(self.mode_n_times)
        self.modeNTimesSpin.valueChanged.connect(self.update_n_times)
        self.insertActionCombo.currentTextChanged.connect(self.insert_action)

    def insert_action(self) -> None:
        try:
            sel_index: Optional[
                QModelIndex
            ] = self.actionList.selectedIndexes()[0]
        except IndexError:
            sel_index = None

        what = self.insertActionCombo.currentIndex()
        if what == 0:  # Default
            return
        if what == 1:  # Press Key
            type = "press_key"
            value = ""
        elif what == 2:  # Release Key
            type = "release_key"
            value = ""
        elif what == 3:  # Delay
            type = "delay"
            value = 50
        elif what == 4:  # Left Mouse Button
            type = "left_mouse_button"
            value = None
        elif what == 5:  # Middle Mouse Button
            type = "middle_mouse_button"
            value = None
        else:  # Right Mouse Button
            type = "right_mouse_button"
            value = None
        action = {
            "type": type,
            "value": value,
        }
        item = QListWidgetItem(self._action_to_str(action))
        if sel_index:
            idx = sel_index.row()
            self.items_actions.insert(idx, (item, action))
            self.actionList.insertItem(idx, item)
        else:
            self.items_actions.append((item, action))
            self.actionList.addItem(item)
        self.insertActionCombo.setCurrentIndex(0)

    def update_n_times(self) -> None:
        self.modeNTimesRadio.setChecked(True)
        self.modeUntilReleasedRadio.setChecked(False)
        self.modeUntilPressedRadio.setChecked(False)
        self.mode_n_times()

    def mode_n_times(self) -> None:
        if self.cur_macro is None:
            show_error(
                self, "Invalid Action",
                "No Macro is selected, please report this.",
            )
            config.log("No current Macro found when deleting action", "ERROR")
            return
        self.cur_macro["mode"] = self.modeNTimesSpin.value()

    def mode_until_pressed(self) -> None:
        if self.cur_macro is None:
            show_error(
                self, "Invalid Action",
                "No Macro is selected, please report this.",
            )
            config.log("No current Macro found when deleting action", "ERROR")
            return
        self.cur_macro["mode"] = "until_pressed_again"

    def mode_until_released(self) -> None:
        if self.cur_macro is None:
            show_error(
                self, "Invalid Action",
                "No Macro is selected, please report this.",
            )
            config.log("No current Macro found when deleting action", "ERROR")
            return
        self.cur_macro["mode"] = "until_released"

    def delete_action(self) -> None:
        try:
            selected = self.actionList.selectedItems()[0]
        except IndexError:
            return
        if self.cur_macro is None:
            show_error(
                self, "Invalid Action",
                "No Macro is selected, please report this.",
            )
            config.log("No current Macro found when deleting action", "ERROR")
            return
        for i, (item, action) in enumerate(self.items_actions):
            if item == selected:
                for j, macro_action in enumerate(self.cur_macro["actions"]):
                    if action is macro_action:
                        del self.cur_macro["actions"][j]
                del self.items_actions[i]
                break
        self.actionList.removeItemWidget(selected)

    def change_action(self) -> None:
        try:
            selected = self.actionList.selectedItems()[0]
        except IndexError:
            return
        cur_action: Optional[config.MACRO_ACTION] = None
        for item, action in self.items_actions:
            if item == selected:
                cur_action = action
        if cur_action is None:
            return

        if cur_action["type"] == "delay":
            mode = "delay"
        elif cur_action["type"] in ("press_key", "release_key"):
            mode = "key"
        else:
            return
        dialog = MacroActionEditor(self, mode, cur_action["value"])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if mode == "delay":
                cur_action["value"] = dialog.delaySpin.value()
            else:
                cur_action["value"] = dialog.keySequence.keySequence(
                ).toString()
            self._refresh_action_list_names()

    def _refresh_action_list_names(self) -> None:
        for item, action in self.items_actions:
            item.setText(self._action_to_str(action))

    def del_macro(self) -> None:
        try:
            selected = self.macroList.selectedItems()[0]
        except IndexError:
            return
        for i, (item, cur_macro) in enumerate(self.items_macros):
            if item == selected:
                for j, macro in enumerate(self.macros):
                    if cur_macro is macro:
                        del self.macros[j]
                del self.items_macros[i]
                break
        self.macroList.removeItemWidget(selected)
        self.cur_macro = None
        self.updateUi()
        self._set_enabled_actions(False)

    def new_macro(self) -> None:
        macro = {
            "name": "New Macro",
            "mode": 1,
            "actions": [],
        }
        self.macros.append(macro)
        item = QListWidgetItem(macro["name"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.macroList.addItem(item)
        self.items_macros.append((item, macro))

    def _set_enabled_actions(self, enabled: bool = True) -> None:
        self.actionList.setEnabled(enabled)
        self.changeBtn.setEnabled(enabled)
        self.deleteBtn.setEnabled(enabled)
        self.modeUntilReleasedRadio.setEnabled(enabled)
        self.modeUntilPressedRadio.setEnabled(enabled)
        self.modeNTimesRadio.setEnabled(enabled)
        self.modeNTimesSpin.setEnabled(enabled)
        self.insertActionCombo.setEnabled(enabled)

    def rename_macro(self, selected: QListWidgetItem) -> None:
        for item, macro in self.items_macros:
            if item == selected:
                macro["name"] = selected.text()

    def macro_list_selection(self) -> None:
        try:
            selected = self.macroList.selectedItems()[0]
        except IndexError:
            return
        cur_macro: Optional[config.MACRO] = None
        for item, macro in self.items_macros:
            if selected == item:
                cur_macro = macro
        if cur_macro is None:
            return
        self.cur_macro = cur_macro
        self._set_enabled_actions(True)
        self.actionList.clear()
        self.items_actions.clear()
        for action in cur_macro["actions"]:
            item = QListWidgetItem(self._action_to_str(action))
            self.items_actions.append((item, action))
            self.actionList.addItem(item)
        self.modeUntilReleasedRadio.blockSignals(True)
        self.modeUntilPressedRadio.blockSignals(True)
        self.modeNTimesRadio.blockSignals(True)
        self.modeNTimesSpin.blockSignals(True)
        if cur_macro["mode"] == "until_released":
            self.modeUntilPressedRadio.setChecked(False)
            self.modeNTimesRadio.setChecked(False)
            self.modeNTimesSpin.setValue(0)
            self.modeUntilReleasedRadio.setChecked(True)
        elif cur_macro["mode"] == "until_pressed_again":
            self.modeNTimesRadio.setChecked(False)
            self.modeNTimesSpin.setValue(0)
            self.modeUntilReleasedRadio.setChecked(False)
            self.modeUntilPressedRadio.setChecked(True)
        elif isinstance(cur_macro["mode"], int):
            self.modeUntilPressedRadio.setChecked(False)
            self.modeUntilReleasedRadio.setChecked(True)
            self.modeNTimesRadio.setChecked(True)
            self.modeNTimesSpin.setValue(cur_macro["mode"])
        self.modeUntilReleasedRadio.blockSignals(False)
        self.modeUntilPressedRadio.blockSignals(False)
        self.modeNTimesRadio.blockSignals(False)
        self.modeNTimesSpin.blockSignals(False)

    def _action_to_str(self, action: config.MACRO_ACTION) -> None:
        name = action["type"].title().replace("_", " ")
        if action["type"] in ("press_key", "release_key", "delay"):
            name += f": {action['value']}"
        return name


class MacroActionEditor(QDialog, Ui_EditAction):  # type: ignore[misc]  # noqa
    def __init__(
        self,
        parent: QWidget,
        type: Union[Literal["delay"], Literal["key"]],
        preset: Union[str, int],
    ) -> None:
        super().__init__(parent)
        self.type = type
        self.preset = preset
        self.setupUi(self)

    def setupUi(self, *args: Any, **kwargs: Any) -> None:
        super().setupUi(*args, **kwargs)
        if self.type == "delay":
            self.delayLabel.setEnabled(True)
            self.delaySpin.setEnabled(True)
            self.keyLabel.setMaximumHeight(0)
            self.keySequence.setMaximumHeight(0)
            if not isinstance(self.preset, int):
                show_error(
                    self, "Invalid Preset",
                    f"Invalid Preset {self.preset} for mode {self.type}",
                )
                config.log(
                    f"Invalid Preset {self.preset} for mode {self.type}",
                    "ERROR",
                )
                self.reject()
                return
            self.delaySpin.setValue(self.preset)
        else:
            self.keyLabel.setEnabled(True)
            self.keySequence.setEnabled(True)
            self.delayLabel.setMaximumHeight(0)
            self.delaySpin.setMaximumHeight(0)
            if not isinstance(self.preset, str):
                show_error(
                    self, "Invalid Preset",
                    f"Invalid Preset {self.preset} for mode {self.type}",
                )
                config.log(
                    f"Invalid Preset {self.preset} for mode {self.type}",
                    "ERROR",
                )
                self.reject()
                return
            self.keySequence.setKeySequence(
                QKeySequence.fromString(self.preset)
            )


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
