import sys
import time
import traceback
from collections import deque
from pathlib import Path
from threading import Thread
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
        self.connected = False
        self.handshaked = False
        self.write_queue: deque[str] = deque()

        self.rotary_encoder_clockwise: Callable[[], None] = lambda: None
        self.rotary_encoder_counterclockwise: Callable[[], None] = lambda: None
        self.status_button_matrix: Callable[
            [list[list[int]]], None] = lambda _: None
        self.status_button_single: Callable[[int], None] = lambda _: None

    def run(self) -> None:
        while True:
            if not self.connected:
                if not self.reconnect():
                    time.sleep(0.01)
                break
            elif not self.handshaked:
                self.ser.read_all()
                self.ser.write(b"HANDSHAKE\n")
                for _ in range(100):
                    if self.ser.in_waiting > 0:
                        if self.ser.read_until() == b"HANDSHAKE":
                            self.handshaked = True
                            break
                else:
                    time.sleep(0.01)
                break

            # We are connected and got a handshake
            if self.write_queue:
                self.ser.write(self.write_queue.pop().encode("utf-8") + b"\n")

            if self.ser.in_waiting > 0:
                line = self.ser.read_until().decode("utf-8")
                self.process_task(line)

    def process_task(self, line: str) -> None:
        task = line.split(" ")
        if task[0] == "EVENT":
            if task[1] == "ROTARYENCODER":
                if task[2] == "CLOCKWISE":
                    self.rotary_encoder_clockwise()
                elif task[2] == "COUNTERCLOCKWISE":
                    self.rotary_encoder_counterclockwise()
        elif task[0] == "STATUS":
            if task[1] == "BUTTON":
                if task[2] == "MATRIX":
                    status = task[3]
                    matrix = []
                    for row in status.split(";"):
                        matrix.append([int(i) for i in row.split(":")])
                    self.status_button_matrix(matrix)
                elif task[2] == "SINGLE":
                    state = task[3]
                    self.status_button_single(int(state))

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            self.connected = True
            self.log(f"Connected to port {self.ser.name}", "DEBUG")
        except serial.SerialException as e:
            self.connected = False
            self.log(f"Failed to connect to serial port ({e})", "DEBUG")
        return self.connected

    def close(self) -> None:
        if self.ser:
            self.ser.close()

    def reconnect(self) -> bool:
        self.close()
        return self.connect()


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
    conn_thread = Thread(target=conn.run, name="buttonbox_serial", daemon=True)
    conn_thread.start()

    try:
        code = app.exec()
    except Exception as e:
        config.log(e, "CRITICAL")
        traceback.print_exc(file=config.LogStream("TRACE"))

    icon.stop()
    sys.exit(code)


if __name__ == "__main__":
    main()
