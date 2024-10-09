import sys
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Callable, Optional

import pystray
import serial
from PIL import Image


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


def start_gui(queue: Queue):
    try:
        from . import config
        from .gui import launch_gui
    except ImportError:
        import config
        from gui import launch_gui

    queue.put(config)
    queue.join()
    conn: Connection = queue.get()
    queue.task_done()

    app, win = launch_gui(conn)
    win.hide()
    queue.put((app, win))
    app.exec()


def main():
    queue = Queue()

    thread = Thread(
        target=start_gui,
        name="Buttonbox-GUI",
        daemon=True,
        args=(queue,),
    )
    thread.start()

    config = queue.get()
    queue.task_done()
    port = config.get_config_value("default_port")
    baudrate = config.get_config_value("baudrate")
    conn = Connection(port, baudrate, config.log, config.log_mc)
    queue.put(conn)
    queue.join()
    app, win = queue.get()
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

    icon.run()


if __name__ == "__main__":
    main()
