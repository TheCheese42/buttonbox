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
    import config  # type: ignore[no-redef]
    from gui import launch_gui  # type: ignore[no-redef]


class Connection:
    def __init__(
        self,
        port: str,
        baudrate: int,
        log: Callable[[str, str], None],
        log_mc: Callable[[str], None],
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.log = log
        self.log_mc = log_mc
        self.ser: Optional[serial.Serial] = None
        self.connected = False
        self.handshaked = False
        self.write_queue: deque[str] = deque()

        self.paused = False
        self.in_history: list[str] = []
        self.out_history: list[str] = []
        self.full_history: list[str] = []

        self.rotary_encoder_clockwise: Callable[[], None] = lambda: None
        self.rotary_encoder_counterclockwise: Callable[[], None] = lambda: None
        self.status_button_matrix: Callable[
            [list[list[int]]], None] = lambda _: None
        self.status_button_single: Callable[[int], None] = lambda _: None
        self.mc_debug: Callable[[str], None] = lambda _: None
        self.mc_warning: Callable[[str], None] = lambda _: None
        self.mc_error: Callable[[str], None] = lambda _: None
        self.mc_critical: Callable[[str], None] = lambda _: None

    def write(self, cmd: str) -> None:
        self.write_queue.append(cmd)

    def run(self) -> None:
        while True:
            if self.paused:
                time.sleep(0.1)
                continue

            if not self.ser or not self.connected or not self.ser.is_open:
                if not self.reconnect():
                    time.sleep(1)
                continue
            elif not self.handshaked:
                try:
                    self.ser.read_all()
                except serial.SerialException:
                    pass
                try:
                    self.ser.write(b"HANDSHAKE\n")
                except serial.SerialException as e:
                    self.log(f"Error writing handshake: {e}", "WARNING")
                    continue
                for _ in range(100):
                    try:
                        in_waiting = self.ser.in_waiting
                    except (OSError, TypeError) as e:
                        self.log(
                            "Received error when checking for available "
                            f"bytes: {e}",
                            "WARNING",
                        )
                    if in_waiting > 0:
                        try:
                            msg = self.ser.read_until().decode("utf-8")
                        except serial.SerialException as e:
                            self.log(f"Error reading potential handshake: {e}",
                                     "WARNING")
                            continue
                        if msg.startswith(
                            "HANDSHAKE"
                        ):
                            self.log(
                                f"Received HANDSHAKE on port {self.ser.name}",
                                "DEBUG"
                            )
                            self.handshaked = True
                            break
                    time.sleep(0.01)
                else:
                    time.sleep(1)
                continue

            # We are connected and got a handshake

            if self.write_queue:
                cmd = self.write_queue.popleft()
                try:
                    self.ser.write(cmd.encode("utf-8") + b"\n")
                except serial.SerialException as e:
                    self.log(f"Error writing '{cmd}': {e}", "WARNING")
                    self.write_queue.append(cmd)
                    continue
                self.log(f"Wrote {cmd} to port {self.ser.name}", "DEBUG")
                self.out_history.append(cmd)
                self.full_history.append(f"[OUT] {cmd}\n")

            try:
                in_waiting = self.ser.in_waiting
            except (OSError, TypeError) as e:
                self.log(
                    f"Received error when checking for available bytes: {e}",
                    "WARNING",
                )
            if in_waiting > 0:
                try:
                    line = self.ser.read_until().decode("utf-8")
                except serial.SerialException as e:
                    self.log(f"Error reading waiting bytes: {e}",
                             "WARNING")
                    continue
                self.log(f"Received {line.replace('\n', '')} from port "
                         f"{self.ser.name}", "DEBUG")
                self.in_history.append(line)
                # Double space for alignment with [OUT]
                self.full_history.append(f"[IN]  {line}")
                self.process_task(line)
            time.sleep(0.1)

    def disconnect(self) -> None:
        self.connected = False
        self.handshaked = False

    def process_task(self, line: str) -> None:
        task = line.split()
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
                        if "\n" in row or not row:
                            continue
                        matrix.append([int(i) for i in row.split(":")])
                    self.status_button_matrix(matrix)
                elif task[2] == "SINGLE":
                    state = task[3]
                    self.status_button_single(int(state))
        elif task[0] == "DEBUG":
            self.mc_debug(" ".join(task[1:]))
            config.log_mc(line)
        elif task[0] == "WARNING":
            self.mc_warning(" ".join(task[1:]))
            config.log_mc(line)
        elif task[0] == "ERROR":
            self.mc_error(" ".join(task[1:]))
            config.log_mc(line)
        elif task[0] == "CRITICAL":
            self.mc_critical(" ".join(task[1:]))
            config.log_mc(line)
        else:
            self.log(f"Received invalid task {line}", "WARNING")

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            self.connected = True
            self.log(f"Connected to port {self.ser.name}", "DEBUG")
        except serial.SerialException as e:
            self.connected = False
            self.log(f"Failed to connect to serial port ({e})", "DEBUG")
        self.handshaked = False
        return self.connected

    def close(self) -> None:
        if self.ser:
            self.ser.close()

    def reconnect(self) -> bool:
        self.close()
        return self.connect()


def main() -> None:
    config.log("BUTTONBOX - Client", "INFO")
    port = config.get_config_value("default_port")
    config.log(f"Default port: {port}", "INFO")
    baudrate = config.get_config_value("baudrate")
    config.log(f"Using baudrate {baudrate}", "INFO")
    conn = Connection(port, baudrate, config.log, config.log_mc)
    config.log("Launching GUI...", "INFO")
    app, win = launch_gui(conn)
    tray_icon = Image.open(Path(__file__).parent / "icons" / "cube-icon.png")

    def show_gui(_) -> None:  # type: ignore[no-untyped-def]
        win.show()

    def quit_app(_) -> None:  # type: ignore[no-untyped-def]
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
    config.log("Started system tray icon", "INFO")
    win.hide()
    conn_thread = Thread(target=conn.run, name="buttonbox_serial", daemon=True)
    config.log("Starting serial connection event loop...", "INFO")
    conn_thread.start()

    try:
        code = app.exec()
    except (KeyboardInterrupt, EOFError) as e:
        config.log(f"Received {e.__class__.__name__}, exiting cleanly", "INFO")
    except Exception as e:
        config.log(str(e), "CRITICAL")
        traceback.print_exc(file=config.LogStream("TRACE"))

    icon.stop()
    conn.close()
    win.close()
    app.quit()
    sys.exit(code)


if __name__ == "__main__":
    main()
