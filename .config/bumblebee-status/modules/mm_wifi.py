"""Cached NetworkManager link state and an isolated Rofi helper launch."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.local/lib'))
from mountain_mist.network import NetworkManager, Wifi
from mountain_mist.runtime import CommandError, start_helper
import core.input
import core.module


class Module(core.module.Module):
    def __init__(self, config, theme):
        super().__init__(config, theme, [])
        self.add_widget(self.full_text)
        self.set('interval', self.parameter('interval', 15))
        self.background = True
        self._wifi = Wifi('unavailable')
        self._helper = None
        core.input.register(self, core.input.LEFT_MOUSE, self.open_menu)

    def full_text(self, _widget):
        return self._wifi.text

    def state(self, _widget):
        return [self._wifi.state]

    def update(self):
        try:
            self._wifi = NetworkManager().status()
        except (CommandError, ValueError):
            self._wifi = Wifi('unavailable')
        if self._helper:
            self._helper.poll()

    def open_menu(self, _event):
        if self._helper and self._helper.poll() is None:
            return
        try:
            self._helper = start_helper('rofi-network')
        except OSError:
            self._wifi = Wifi('unavailable')
