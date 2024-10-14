from typing import Callable, Optional, Union
from subprocess import getoutput

try:
    from . import config
except ImportError:
    import config


GAME_ACTION_ENTRY = dict[str, str]
BUTTON_ENTRY = dict[
    str, Union[
        None,
        str,
        GAME_ACTION_ENTRY,
    ]
]
PROFILE = dict[
    str, Union[
        None,
        str,
        BUTTON_ENTRY,
        list[list[BUTTON_ENTRY]],
    ]
]


def exec_entry(entry: BUTTON_ENTRY) -> None:
    if entry["type"] is None:
        return
    elif entry["type"] == "command":
        getoutput(entry["value"], encoding="utf-8")
    elif entry["type"] == "game_action":
        game = entry["value"]["game"]
        action = entry["value"]["action"]
        getattr(GAME_LOOKUP[game], action)()


class Profile:
    def __init__(self, data: PROFILE) -> None:
        self.data = data

    @property
    def name(self) -> str:
        return self.data["name"]

    @name.setter
    def name(self, val: str) -> None:
        self.data["name"] = val

    @property
    def auto_activate(self) -> Optional[str]:
        """The callable used for autodetection"""
        return self.data["auto_activate"]

    @auto_activate.setter
    def auto_activate(self, val: Optional[str]) -> None:
        self.data["auto_activate"] = val

    @property
    def led_profile(self) -> Optional[str]:
        """The callable managing the LEDs"""
        return self.data["led_profile"]

    @led_profile.setter
    def led_profile(self, val: Optional[str]) -> None:
        self.data["led_profile"] = val

    @property
    def button_single(self) -> BUTTON_ENTRY:
        return self.data["button_single"]

    @button_single.setter
    def button_single(self, val: BUTTON_ENTRY) -> None:
        self.data["button_single"] = val

    @property
    def button_matrix(self) -> list[list[BUTTON_ENTRY]]:
        return self.data["button_matrix"]

    @button_matrix.setter
    def button_matrix(self, val: list[list[BUTTON_ENTRY]]) -> None:
        self.data["button_matrix"] = val

    def get_button_matrix_entry_for(self, row: int, col: int) -> BUTTON_ENTRY:
        return self.button_matrix[row][col]

    def set_button_matrix_entry_for(
        self,
        row: int,
        col: int,
        entry: BUTTON_ENTRY,
    ) -> None:
        self.button_matrix[row][col] = entry


class Game:
    def detect(self) -> bool:
        """
        Detect wether the game is currently running.
        """
        return False

    def led_manager(self) -> None:
        """
        Manage the LEDs depending on gameplay.
        """
        return None


class BeamNG(Game):
    pass


GAME_LOOKUP = {
    "beamng": BeamNG,
}
