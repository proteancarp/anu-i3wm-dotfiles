"""One bounded default-sink query shared by separate volume/mute widgets."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.local/lib'))
from mountain_mist.runtime import CommandError, run
import core.input
import core.module


def parse_volume(output):
    match = re.fullmatch(r'\s*Volume:\s*([0-9]+(?:\.[0-9]+)?)\s*(\[MUTED\])?\s*', output)
    if not match:
        raise ValueError('invalid wpctl volume')
    try:
        volume = Decimal(match[1])
    except InvalidOperation as exc:
        raise ValueError('invalid wpctl volume') from exc
    if not volume.is_finite() or not 0 <= volume <= 10:
        raise ValueError('invalid wpctl volume')
    return int((volume * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)), bool(match[2])


class Module(core.module.Module):
    def __init__(self, config, theme):
        super().__init__(config, theme, [])
        self.volume = self.add_widget(self.full_text, name='volume')
        self.mute = self.add_widget(self.full_text, name='mute')
        self.set('interval', self.parameter('interval', 5))
        self.background = True
        self._snapshot = (None, False)
        core.input.register(self.volume, core.input.LEFT_MOUSE, self.ignore)
        core.input.register(self.volume, core.input.WHEEL_UP, self.increase)
        core.input.register(self.volume, core.input.WHEEL_DOWN, self.decrease)
        core.input.register(self.mute, core.input.LEFT_MOUSE, self.toggle)
        # Consume wheel events here so they cannot reach the engine's global
        # wheel bindings (workspace switching) or the adjacent volume control.
        core.input.register(self.mute, core.input.WHEEL_UP, self.ignore)
        core.input.register(self.mute, core.input.WHEEL_DOWN, self.ignore)

    def full_text(self, widget):
        percent, muted = self._snapshot
        if widget is self.mute:
            return 'MUTE ?' if percent is None else 'MUTED' if muted else 'MUTE'
        return 'VOL ?' if percent is None else f'VOL {percent}%'

    def state(self, widget):
        percent, muted = self._snapshot
        kind = 'mute' if widget is self.mute else 'volume'
        state = 'unavailable' if percent is None else 'muted' if kind == 'mute' and muted else 'normal'
        return [kind, state]

    def update(self):
        try:
            value = run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'], timeout=2).stdout
            percent, muted = parse_volume(value)
            self._snapshot = (percent, muted)
        except (CommandError, ValueError):
            self._snapshot = (None, False)

    def change(self, args):
        try:
            run(['wpctl', *args], timeout=2)
        except CommandError:
            self._snapshot = (None, False)

    def ignore(self, _event):
        pass

    def toggle(self, _event):
        self.change(['set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'])

    def increase(self, _event):
        self.change(['set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%+'])

    def decrease(self, _event):
        self.change(['set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%-'])
