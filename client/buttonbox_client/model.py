import json
import sys
from itertools import chain
from pathlib import Path
from subprocess import getoutput
from typing import Any, Callable, Optional, Union

try:
    from . import config
except ImportError:
    import config  # type: ignore[no-redef]


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
        getoutput(entry["value"], encoding="utf-8")  # type: ignore[arg-type]
    elif entry["type"] == "game_action":
        game = entry["value"]["game"]  # type: ignore[index]
        action = entry["value"]["action"]  # type: ignore[index]
        getattr(GAME_LOOKUP[game], action)()


class Profile:
    def __init__(self, data: PROFILE) -> None:
        self.data = data

    @classmethod
    def empty(cls) -> "Profile":
        with open(Path(__file__).parent / "empty_profile.json") as fp:
            return cls(json.load(fp))

    @property
    def name(self) -> str:
        return self.data["name"]  # type: ignore[return-value]

    @name.setter
    def name(self, val: str) -> None:
        self.data["name"] = val

    @property
    def auto_activate(self) -> Optional[str]:
        """The callable used for autodetection"""
        return self.data["auto_activate"]  # type: ignore[return-value]

    @auto_activate.setter
    def auto_activate(self, val: Optional[str]) -> None:
        self.data["auto_activate"] = val

    @property
    def led_profile(self) -> Optional[str]:
        """The callable managing the LEDs"""
        return self.data["led_profile"]  # type: ignore[return-value]

    @led_profile.setter
    def led_profile(self, val: Optional[str]) -> None:
        self.data["led_profile"] = val

    @property
    def button_single(self) -> BUTTON_ENTRY:
        return self.data["button_single"]  # type: ignore[return-value]

    @button_single.setter
    def button_single(self, val: BUTTON_ENTRY) -> None:
        self.data["button_single"] = val

    @property
    def button_matrix(self) -> list[list[BUTTON_ENTRY]]:
        return self.data["button_matrix"]  # type: ignore[return-value]

    @button_matrix.setter
    def button_matrix(self, val: list[list[BUTTON_ENTRY]]) -> None:
        self.data["button_matrix"] = val

    def get_button_matrix_entry_for(self, row: int, col: int) -> BUTTON_ENTRY:
        return self.button_matrix[col][row]

    def set_button_matrix_entry_for(
        self,
        row: int,
        col: int,
        entry: BUTTON_ENTRY,
    ) -> None:
        self.button_matrix[col][row] = entry


class Game:
    game_name = "Game"

    @staticmethod
    def actions() -> list[Callable[[Any], None]]:
        return []

    @staticmethod
    def name_for_action(action: Callable[[Any], None]) -> Optional[str]:
        lookup: dict[Callable[[Any], None], str] = {}
        return lookup.get(action)

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
    game_name = "BeamNG"

    @staticmethod
    def actions() -> list[Callable[[Any], None]]:
        return [
            BeamNG.test,
        ]

    @staticmethod
    def name_for_action(action: Callable[[Any], None]) -> Optional[str]:
        lookup: dict[Callable[[Any], None], str] = {
            BeamNG.test: "Test",
        }
        return lookup.get(action)

    def test(self) -> None:
        """Just testing."""


GAME_LOOKUP = {
    "beamng": BeamNG,
}


GAME_ACTIONS: list[Callable[[Any], None]] = list(
    chain(*[game.actions() for game in GAME_LOOKUP.values()])
)


def load_profiles() -> dict[int, Profile]:
    with open(config.PROFILES_PATH, "r", encoding="utf-8") as fp:
        profiles: list[PROFILE] = json.load(fp)

    profiles_dict = {}
    for i, profile in enumerate(profiles):
        profiles_dict[i] = Profile(profile)

    return profiles_dict


def save_profiles(profiles: dict[int, Profile]) -> None:
    profiles_list = []
    for profile in profiles.values():
        profiles_list.append(profile.data)

    with open(config.PROFILES_PATH, "w", encoding="utf-8") as fp:
        json.dump(profiles_list, fp)


def sort_dict(d: dict[Any, Any]) -> dict[Any, Any]:
    new = {}
    for i in sorted(d.keys()):
        new[i] = d[i]
    return new


def rebuild_numbered_dict(d: dict[Any, Any]) -> dict[Any, Any]:
    new = {}
    for i, profile in enumerate(sort_dict(d).values()):
        new[i] = profile
    return new


def reverse_lookup(d: dict[Any, Any], value: Any) -> Any:
    for key, val in d.items():
        if val == value:
            return key
    raise KeyError("Key for value " + str(value) + " not found")


def find_class(method: Callable[..., Any]) -> Optional[type]:
    module = sys.modules.get(method.__module__)
    if module is None:
        return None
    cls: type = getattr(module, method.__qualname__.split('.')[0])
    return cls
