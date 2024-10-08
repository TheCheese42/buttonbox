from PyQt6.QtWidgets import QMainWindow, QDialog
from ui.window import Ui_MainWindow
import webbrowser
from subprocess import getoutput


try:
    from . import version
    from . import config
    config.init_config()
except ImportError:
    import version
    import config
    config.init_config()


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__(None)
        self.setupUi(self)
        self.connectSignatSlots()
        self.light_stylesheet = self.styleSheet()
        self.dark_stylesheet = """
            QWidget {
                backkground-color: rgb(40, 40, 40);
                color: white;
                selection-background-color: transparent;
            }
            QPlainTextEdit {
                background-color: rgb(60, 60, 60);
            }
            QMenu {
                background-color: rgb(20, 20, 20);
            }
            QMenuBar {
                background-color: rgb(25, 25, 25);
            }
            QMenu:hover {
                background-color: rgb(35, 35, 35);
            }
            QMenu:pressed {
                background-color: rgb(45, 45, 45);
            }
            QCheckbox::indicator:hover {
                color: rgb(50, 50, 50);
            }
            QCheckbox::indicator:pressed {
                background-color: rgb(60, 60, 60);
            }
            QComboBox:selected {
                background-color: rgb(40, 40, 40);
            }
        """
        self.apply_theme()

    def setupUI(self, *agrs, **kwargs):
        super().setupUi(*args, **kwargs)

    def connectSignalsSlots(self):
        pass

    def dark_mode(self):
        dark = self.actionDarkMode.isChecked()
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

    def open_github(self):
        try:
            webbrowser.WindowsDefault().open(
                "https://github.com/asunadawg/buttonbox"
            )
        except Exception:
            getoutput(
                "start https://github.com/asunadawg/buttonbox"
            )


class LicensesDialog(QDialog, Ui_Licenses):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())

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

