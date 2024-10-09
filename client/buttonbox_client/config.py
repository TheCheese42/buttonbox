import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QStandardPaths

CONFIG_DIR = Path(
    QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
) / "Buttonbox"
CONFIG_PATH = CONFIG_DIR / ".config.json"
LOGGER_PATH = CONFIG_DIR / "latest.log"
MC_DEBUG_LOG_PATH = CONFIG_DIR / "mcdebug.log"

DEFAULT_CONFIG = {
    "dark": False,
    "default_port": None,
    "active_profile": "default",
    "baudrate": 9600,
}


def config_exists():
    return CONFIG_PATH.exists()


def create_app_dir():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()


def trunc_log():
    with open(LOGGER_PATH, "w") as fp:
        fp.write("")

    with open(MC_DEBUG_LOG_PATH, "w") as fp:
        fp.write("")


def init_config():
    create_app_dir()
    trunc_log()

    if not config_exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
            json.dump(DEFAULT_CONFIG, fp)


def _get_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _overwrite_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(config, fp)


def get_config_value(key: str):
    try:
        val = _get_config()[key]
    except KeyError:
        val = DEFAULT_CONFIG[key]
    return val


def set_config_value(key: str, value: str):
    config = _get_config()
    config[key] = value
    _overwrite_config(config)


def log(msg: str, level: str = "INFO"):
    with open(LOGGER_PATH, "a", encoding="utf-8") as fp:
        fp.write(f"[{level}] [{datetime.now().isoformat()}] {msg}\n")


def log_mc(msg: str):
    with open(MC_DEBUG_LOG_PATH, "a", encoding="utf-8") as fp:
        fp.write(f"[{datetime.now().isoformat()}] {msg}\n")
