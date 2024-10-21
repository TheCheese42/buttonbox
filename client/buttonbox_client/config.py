import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QStandardPaths

CONFIG_DIR = Path(
    QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
) / "Buttonbox"
CONFIG_PATH = CONFIG_DIR / "config.json"
LOGGER_PATH = CONFIG_DIR / "latest.log"
MC_DEBUG_LOG_PATH = CONFIG_DIR / "mcdebug.log"
SER_HISTORY_PATH = CONFIG_DIR / "serial_history.log"
PROFILES_PATH = CONFIG_DIR / "profiles.json"
KEYBOARD_SHORTCUTS_PATH = CONFIG_DIR / "keyboard_shortcuts.json"
CUSTOM_ACTIONS_PATH = CONFIG_DIR / "custom_actions.json"

LICENSES_PATH = Path(__file__).parent / "licenses"
LICENSE_PATH = LICENSES_PATH / "LICENSE.html"
WINDOWS_LICENSE_PATH = LICENSES_PATH / "OPEN_SOURCE_LICENSES_WINDOWS.html"
LINUX_LICENSE_PATH = LICENSES_PATH / "OPEN_SOURCE_LICENSES_LINUX.html"

DEFAULT_CONFIG = {
    "dark": False,
    "default_port": "COM0" if platform.system() == "Windows" else "/dev/ttyS0",
    "baudrate": 115200,
    "auto_detect_profiles": True,
    "hide_to_tray": True,
}


def config_exists() -> bool:
    return CONFIG_PATH.exists()


def create_app_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def trunc_log() -> None:
    with open(LOGGER_PATH, "w") as fp:
        fp.write("")

    with open(MC_DEBUG_LOG_PATH, "w") as fp:
        fp.write("")


def ensure_profiles_file() -> None:
    if not PROFILES_PATH.exists():
        with open(PROFILES_PATH, "w", encoding="utf-8") as fp:
            fp.write("[]")


def ensure_keyboard_file() -> None:
    if not KEYBOARD_SHORTCUTS_PATH.exists():
        with open(KEYBOARD_SHORTCUTS_PATH, "w", encoding="utf-8") as fp:
            fp.write("[]")


def ensure_custom_actions_file() -> None:
    if not CUSTOM_ACTIONS_PATH.exists():
        with open(CUSTOM_ACTIONS_PATH, "w", encoding="utf-8") as fp:
            fp.write("{}")


def init_config() -> None:
    create_app_dir()
    trunc_log()
    ensure_profiles_file()
    ensure_keyboard_file()
    ensure_custom_actions_file()

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


def get_keyboard_shortcut(game: str, action: str) -> Optional[str]:
    with open(KEYBOARD_SHORTCUTS_PATH, "r", encoding="utf-8") as fp:
        shortcuts: list[dict[str, str]] = json.load(fp)
    for shortcut in shortcuts:
        if shortcut["game"] == game and shortcut["action"] == action:
            return shortcut["shortcut"]
    return None


def set_keyboard_shortcut(game: str, action: str, shortcut: str) -> None:
    with open(KEYBOARD_SHORTCUTS_PATH, "r", encoding="utf-8") as fp:
        shortcuts: list[dict[str, str]] = json.load(fp)
    exists = False
    for entry in shortcuts:
        if entry["game"] == game and entry["action"] == action:
            exists = True
            entry["shortcut"] = shortcut
    if not exists:
        shortcuts.append({
            "game": game,
            "action": action,
            "shortcut": shortcut
        })
    with open(KEYBOARD_SHORTCUTS_PATH, "w", encoding="utf-8") as fp:
        json.dump(shortcuts, fp)


def get_custom_actions() -> dict[str, str]:
    with open(CUSTOM_ACTIONS_PATH, "r", encoding="utf-8") as fp:
        actions: dict[str, str] = json.load(fp)
    return actions


def set_custom_actions(actions: dict[str, str]) -> None:
    with open(CUSTOM_ACTIONS_PATH, "w", encoding="utf-8") as fp:
        json.dump(actions, fp)


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
