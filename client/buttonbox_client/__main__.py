import sys
from pathlib import Path
from typing import Callable, Optional

import pystray
import serial
from PIL import Image

try:
    from . import config
    from .gui import launch_gui
except ImportError:
    import config
    from gui import launch_gui


class Connection:
    def __init__(
        self,
        port: str,
        baudrate: int,
        log: Callable[[str, str], None],
        log_mc: Callable[[str, str], None],
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.log = log
        self.log_mc = log_mc
        self.ser: Optional[serial.Serial] = None

    def connect(self) -> None:
        self.close()
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            self.log(f"Connected to port {self.ser.name}", "DEBUG")
        except serial.SerialException as e:
            self.log(f"Failed to connect to serial port ({e})", "DEBUG")

    def close(self) -> None:
        if self.ser:
            self.ser.close()

    def reconnect(self) -> None:
        self.close()
        self.connect()


def main():
    port = config.get_config_value("default_port")
    baudrate = config.get_config_value("baudrate")
    conn = Connection(port, baudrate, config.log, config.log_mc)
    app, win = launch_gui(conn)
    tray_icon = Image.open(Path(__file__).parent / "icons" / "cube-icon.png")

    def show_gui(_):
        win.show()

    def quit_app(_):
        conn.close()
        win.close()
        app.quit()
        sys.exit(0)

    icon = pystray.Icon(
        "Buttonbox", tray_icon, "Buttonbox",
        menu=pystray.Menu(
            pystray.MenuItem(
                "Show Graphical Interface",
                show_gui,
                default=True,
            ),
            pystray.MenuItem("Quit", quit_app)
        )
    )

    icon.run_detached()
    win.hide()
    code = app.exec()
    icon.stop()
    sys.exit(code)


if __name__ == "__main__":
    main()
