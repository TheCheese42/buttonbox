import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QStandardPaths

CONFIG_DIR = Path(
    QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
) / "Buttonbox"
CONFIG_PATH = CONFIG_DIR / ".config.json"
LOGGER_PATH = CONFIG_DIR / "latest.log"
MC_DEBUG_LOG_PATH = CONFIG_DIR / "mcdebug.log"
SER_HISTORY_PATH = CONFIG_DIR / "serial_history.log"
PROFILES_PATH = CONFIG_DIR / "profiles"

DEFAULT_CONFIG = {
    "dark": False,
    "default_port": "COM0" if platform.system() == "Windows" else "/dev/ttyS0",
    "active_profile": "default",
    "baudrate": 9600,
}


def config_exists() -> bool:
    return CONFIG_PATH.exists()


def create_app_dir() -> None:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()


def trunc_log() -> None:
    with open(LOGGER_PATH, "w") as fp:
        fp.write("")

    with open(MC_DEBUG_LOG_PATH, "w") as fp:
        fp.write("")


def init_config() -> None:
    create_app_dir()
    trunc_log()

    if not config_exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
            json.dump(DEFAULT_CONFIG, fp)


def _get_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
        conf: dict[str, Any] = json.load(fp)
        return conf


def _overwrite_config(config: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(config, fp)


def get_config_value(key: str) -> Any:
    try:
        val = _get_config()[key]
    except KeyError:
        val = DEFAULT_CONFIG[key]
    return val


def set_config_value(key: str, value: str) -> None:
    config = _get_config()
    config[key] = value
    _overwrite_config(config)


def log(msg: str, level: str = "INFO") -> None:
    with open(LOGGER_PATH, "a", encoding="utf-8") as fp:
        fp.write(f"[{level}] [{datetime.now().isoformat()}] {msg}\n")


def log_mc(msg: str) -> None:
    with open(MC_DEBUG_LOG_PATH, "a", encoding="utf-8") as fp:
        fp.write(f"[{datetime.now().isoformat()}] {msg}\n")


class LogStream:
    def __init__(self, level: str = "INFO") -> None:
        self.level = level

    def write(self, text: str) -> None:
        log(text, self.level)
