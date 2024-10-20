import json
import sys
import time
from contextlib import contextmanager
from functools import partial
from itertools import chain
from pathlib import Path
from subprocess import getoutput
from typing import TYPE_CHECKING, Any, Callable, Generator, Optional, Union

from pynput.keyboard import Controller as KController
from pynput.keyboard import Key, KeyCode
from pynput.keyboard import Listener as KListener
from pynput.mouse import Button
from pynput.mouse import Controller as MController
from pynput.mouse import Listener as MListener
from PyQt6.QtWidgets import QRadioButton

try:
    from . import config
except ImportError:
    import config  # type: ignore[no-redef]

if TYPE_CHECKING:
    from .__main__ import Connection
    from .gui import Window

STATE = {True: "HIGH", False: "LOW"}

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


SHORTCUT_ACTIONS: list[Callable[[Any, bool], None]] = []


def register_shortcut_action(
    func: Callable[[Any, bool], Any]
) -> Callable[[Any, bool], Any]:
    SHORTCUT_ACTIONS.append(func)
    return func


def exec_entry(
    entry: BUTTON_ENTRY,
    state: bool,
    games_to_instance: dict[type["Game"], "Game"],
) -> None:
    if entry["type"] is None:
        return
    elif entry["type"] == "command":
        if state:
            getoutput(entry["value"], encoding="utf-8")  # type: ignore[arg-type]  # noqa
    elif entry["type"] == "game_action":
        game = entry["value"]["game"]  # type: ignore[index]
        action = entry["value"]["action"]  # type: ignore[index]
        instance = games_to_instance[GAME_LOOKUP[game]]
        getattr(instance, action)(state)


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
        return self.button_matrix[row][col]

    def set_button_matrix_entry_for(
        self,
        row: int,
        col: int,
        entry: BUTTON_ENTRY,
    ) -> None:
        self.button_matrix[row][col] = entry

    def led_manager_method(self) -> Optional[Callable[["Game"], None]]:
        if not self.led_profile:
            return None
        game = GAME_LOOKUP[self.led_profile]
        return game.led_manager

    def auto_activate_method(self) -> Optional[Callable[["Game"], bool]]:
        if not self.auto_activate:
            return None
        game = GAME_LOOKUP[self.auto_activate]
        return game.detect


class TestProfile(Profile):
    def __init__(self) -> None:
        self.data = Profile.empty().data
        self.led_profile = "test"
        self.button_single["type"] = "game_action"
        self.button_single["value"] = {
            "game": "test",
            "action": "button_single_state",
        }
        for i, row in enumerate(self.button_matrix):
            for j, button in enumerate(row):
                button["type"] = "game_action"
                button["value"] = {
                    "game": "test",
                    "action": f"button_matrix_state_{i}{j}"
                }


class Controller:
    def __init__(self, delay: float = 0.01) -> None:
        """
        :param delay: Delay to wait between press and release, defaults to 0.01
        :type delay: float, optional
        """
        self.kc = KController()
        self.mc = MController()
        self.delay = delay
        self.keys_pressed: set[Union[Key, KeyCode]] = set()
        self.btns_pressed = set(Button)

    def on_key_pressed(self, key: Union[Key, KeyCode]) -> None:
        self.keys_pressed.add(key)

    def on_key_released(self, key: Union[Key, KeyCode]) -> None:
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)

    def on_btn_click(self, x: int, y: int, btn: Button, pressed: bool) -> None:
        if pressed:
            self.btns_pressed.add(btn)
        else:
            if btn in self.btns_pressed:
                self.btns_pressed.remove(btn)

    def is_pressed(self, thing: Union[Key, KeyCode, Button]) -> bool:
        if isinstance(thing, Key) or isinstance(thing, KeyCode):
            return thing in self.keys_pressed
        return thing in self.btns_pressed

    def press(
        self,
        key: Optional[Key] = None,
        but: Optional[Button] = None,
    ) -> None:
        if key:
            self.kc.press(key)
        if but:
            self.mc.press(but)

    def release(
        self,
        key: Optional[Key] = None,
        but: Optional[Button] = None,
    ) -> None:
        if key:
            self.kc.release(key)
        if but:
            self.mc.release(but)

    def tap(
        self,
        key: Optional[Key] = None,
        but: Optional[Button] = None,
        delay: Optional[float] = None,
    ) -> None:
        """Press and release a key and/or button with self.delay in between."""
        self.press(key, but)
        time.sleep(self.delay if delay is None else delay)
        self.release(key, but)

    @contextmanager
    def mod(
        self, *keys: tuple[Union[Key, KeyCode]]
    ) -> Generator[None, None, None]:
        """
        Contextmanager to execute a block with some keys pressed. Checks and
        preserves the previous key states of modifiers.
        """
        to_be_released: list[Key] = []
        for key in keys:
            if not self.is_pressed(key):
                self.press(key)
                to_be_released.append(key)

        try:
            yield
        finally:
            for key in reversed(to_be_released):
                self.release(key)

    def ctrl(
        self,
        key: Optional[Union[Key, KeyCode]] = None,
        but: Optional[Button] = None,
    ) -> None:
        """Tap a key and/or button together with CTRL."""
        with self.mod(Key.ctrl):
            self.press(key, but)

    def shift(
        self,
        key: Optional[Union[Key, KeyCode]] = None,
        but: Optional[Button] = None,
    ) -> None:
        """Tap a key and/or button together with SHIFT."""
        with self.mod(Key.shift):
            self.press(key, but)

    def alt(
        self,
        key: Optional[Union[Key, KeyCode]] = None,
        but: Optional[Button] = None,
    ) -> None:
        """Tap a key and/or button together with ALT."""
        with self.mod(Key.alt):
            self.press(key, but)

    def alt_gr(
        self,
        key: Optional[Union[Key, KeyCode]] = None,
        but: Optional[Button] = None,
    ) -> None:
        """Tap a key and/or button together with ALT GR."""
        with self.mod(Key.alt_gr):
            self.press(key, but)

    def cmd(
        self,
        key: Optional[Union[Key, KeyCode]] = None,
        but: Optional[Button] = None,
    ) -> None:
        """Tap a key and/or button together with CMD."""
        with self.mod(Key.cmd):
            self.press(key, but)


def start_controller() -> Controller:
    controller = Controller()
    kl = KListener(
        on_press=controller.on_key_pressed,
        on_release=controller.on_key_released,
    )
    ml = MListener(
        on_click=controller.on_btn_click,
    )
    kl.start()
    ml.start()
    return controller


class Game:
    game_name = "Game"
    priority = 1
    hidden = False

    def __init__(self, conn: "Connection") -> None:
        self.conn = conn

    @staticmethod
    def actions() -> list[Callable[[Any, bool], None]]:
        return []

    @staticmethod
    def name_for_action(action: Callable[[Any, bool], None]) -> Optional[str]:
        lookup: dict[Callable[[Any, bool], None], str] = {}
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

    def _led_left(self, state: bool) -> None:
        self.conn.write(f"LED {STATE[state]} LEFT")

    def _led_middle(self, state: bool) -> None:
        self.conn.write(f"LED {STATE[state]} MIDDLE")

    def _led_right(self, state: bool) -> None:
        self.conn.write(f"LED {STATE[state]} RIGHT")

    def _led_extra(self, state: bool) -> None:
        self.conn.write(f"LED {STATE[state]} EXTRA")


class Default(Game):
    game_name = "Default"
    priority = 0

    def __init__(self, conn: "Connection") -> None:
        super().__init__(conn)
        self.led_man_cooldown = 1.0
        self.led_man_last = 0.0

    def detect(self) -> bool:
        return True

    def led_manager(self) -> None:
        if time.time() - self.led_man_cooldown >= self.led_man_last:
            self._led_left(True)
            self._led_middle(True)
            self._led_right(True)
            self._led_extra(True)
        self.led_man_last = time.time()


class TestGame(Game):
    game_name = "Test"
    priority = 0
    hidden = True

    def __init__(self, conn: "Connection", win: "Window") -> None:
        super().__init__(conn)
        self.win = win

        # Allow calling the lambdas using getattr()
        for action in self.actions():
            if action.__name__ == "button_single_state":
                continue
            part = partial(action, self)
            setattr(self, action.__name__, part)

    def button_single_state(self, state: bool) -> None:
        self.win.tbs0.setChecked(state)

    def button_matrix_state(self, i: int, state: bool) -> None:
        self._get_btn(i).setChecked(state)

    def _get_btn(self, i: int) -> QRadioButton:
        attr = f"tb{i:02}"
        btn: QRadioButton = getattr(self.win, attr)
        return btn

    @staticmethod
    def actions() -> list[Callable[[Any, bool], None]]:
        acts: list[Callable[[TestGame, bool], None]] = [
            TestGame.button_single_state
        ]
        matrix = []
        for i in range(6):
            row = []
            for j in range(3):
                row.append(int(str(i) + str(j)))
            matrix.append(row)

        def create_lambda(index: int) -> Callable[[Any, bool], None]:
            # Need to create a lambda using an inner function to prevent
            # modifying the index in the outer scope. This would make all
            # lambdas have 52 as index, instead of their respective indices.
            return lambda self, state: TestGame.button_matrix_state(
                self, index, state
            )

        for i in chain(*matrix):
            lamb = create_lambda(i)
            lamb.__name__ = f"button_matrix_state_{i:02}"
            acts.append(lamb)

        return acts

    @staticmethod
    def name_for_action(action: Callable[[Any, bool], None]) -> Optional[str]:
        lookup: dict[Callable[[Any, bool], None], str] = {}
        return lookup.get(action)

    def led_manager(self) -> None:
        self._led_extra(self.win.td0.isChecked())
        self._led_left(self.win.td1.isChecked())
        self._led_middle(self.win.td2.isChecked())
        self._led_right(self.win.td3.isChecked())


class Custom(Game):
    game_name = "Custom"

    def __init__(self, conn: "Connection") -> None:
        super().__init__(conn)
        self._actions: list[Callable[[Any, bool], None]] = []

    @staticmethod
    def action() -> list[Callable[[Any, bool], None]]:
        return []  # TODO

    @staticmethod
    def name_for_action(action: Callable[[Any, bool], None]) -> Optional[str]:
        lookup: dict[Callable[[Any, bool], None], str] = {}  # TODO
        return lookup.get(action)

    def add_action(self, action: Callable[[Any, bool], None]) -> None:
        self._actions.append(action)

    def remove_action(self, action: Callable[[Any, bool], None]) -> None:
        self._actions.remove(action)

    def get_actions(self) -> list[Callable[[Any, bool], None]]:
        return self._actions


class BeamNG(Game):
    game_name = "BeamNG"

    @staticmethod
    def actions() -> list[Callable[[Any, bool], None]]:
        return [
            BeamNG.test,
        ]

    @staticmethod
    def name_for_action(action: Callable[[Any, bool], None]) -> Optional[str]:
        lookup: dict[Callable[[Any, bool], None], str] = {
            BeamNG.test: "Test",
        }
        return lookup.get(action)

    @register_shortcut_action
    def test(self, state: bool) -> None:
        """Just testing."""


GAME_LOOKUP: dict[str, type[Game]] = {
    "game": Game,
    "default": Default,
    "beamng": BeamNG,
    "test": TestGame,
    "custom": Custom,
}


GAME_ACTIONS: list[Callable[[Any, bool], None]] = list(
    chain(
        *[game.actions() for game in GAME_LOOKUP.values() if not game.hidden]
    )
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
