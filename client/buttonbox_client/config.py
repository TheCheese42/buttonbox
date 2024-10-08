import json
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


def config_exists():
    return CONFIG_PATH.exists()


def create_app_dir():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()


def init_config():
    create_app_dir()

    if not config_exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "dark": False,
                    "default_port": None,
                    "active_profile": "default",
                }, fp
            )


def _get_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _overwrite_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        json.dump(config, fp)


def get_config_value(key: str):
    return _get_config()[key]


def set_config_value(key: str, value: str):
    config = _get_config()
    config[key] = value
    _overwrite_config(config)
