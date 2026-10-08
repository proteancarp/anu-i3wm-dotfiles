"""NetworkManager's cached link state, not an Internet connectivity probe."""

from dataclasses import dataclass
import re

from .runtime import CommandError, label, run


def fields(line, count):
    """Decode nmcli -t --escape yes: only colon/backslash may be escaped."""
    result, current, escaped = [], [], False
    for char in line:
        if escaped:
            if char not in (':', '\\'):
                raise ValueError('invalid nmcli escape')
            current.append(char)
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == ':':
            result.append(''.join(current))
            current = []
        else:
            current.append(char)
    result.append(''.join(current))
    if escaped or len(result) != count:
        raise ValueError('invalid nmcli fields')
    return result


@dataclass(frozen=True)
class AccessPoint:
    ssid: str
    signal: int | None
    security: str
    bssid: str
    active: bool = False


@dataclass(frozen=True)
class Wifi:
    state: str
    interface: str = ''
    ssid: str = ''
    signal: int | None = None

    @property
    def text(self):
        if self.state == 'connected':
            strength = f' {self.signal}%' if self.signal is not None else ''
            return f'WiFi {label(self.ssid or "hidden", 20)}{strength}'
        return 'WiFi ' + {'disabled': 'off', 'disconnected': 'down',
                          'connecting': 'connecting'}.get(self.state, '?')


class NetworkManager:
    def __init__(self, runner=run):
        self.runner = runner

    def query(self, columns, *args):
        return self.runner(['nmcli', '-t', '-e', 'yes', '-c', 'no', '-f', columns,
                            *args], timeout=2).stdout

    def radio(self):
        value = self.runner(['nmcli', '-t', '-c', 'no', 'radio', 'wifi'], timeout=2).stdout.strip()
        if value not in ('enabled', 'disabled'):
            raise ValueError('unknown radio state')
        return value == 'enabled'

    def devices(self):
        rows = [fields(line, 3) for line in self.query('DEVICE,TYPE,STATE', 'device', 'status').splitlines()]
        devices = [(name, state) for name, kind, state in rows if kind == 'wifi' and name]
        # Prefer the active device if multiple adapters are present.
        return sorted(devices, key=lambda item: (not item[1].startswith('connected'),
                                                 not item[1].startswith('connecting'), item[0]))

    def access_points(self, interface):
        output = self.query('IN-USE,SSID,SIGNAL,SECURITY,BSSID',
                            'device', 'wifi', 'list', '--rescan', 'no', 'ifname', interface)
        points = []
        for line in output.splitlines():
            active, ssid, strength, security, bssid = fields(line, 5)
            if active not in ('', '*') or not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', bssid):
                raise ValueError('invalid access point')
            signal = None if strength in ('', '--') else int(strength)
            if signal is not None and not 0 <= signal <= 100:
                raise ValueError('invalid signal')
            points.append(AccessPoint(ssid, signal, security, bssid, active == '*'))
        return points

    def status(self):
        if not self.radio():
            return Wifi('disabled')
        devices = self.devices()
        if not devices:
            return Wifi('unavailable')
        interface, state = devices[0]
        if state.startswith('connecting'):
            return Wifi('connecting', interface)
        if state.startswith('connected'):
            active = next((ap for ap in self.access_points(interface) if ap.active), None)
            if active is None:
                return Wifi('unavailable', interface)
            return Wifi('connected', interface, active.ssid, active.signal)
        if state in ('disconnected', 'unavailable', 'unmanaged') or state.startswith('disconnecting'):
            return Wifi('disconnected', interface)
        return Wifi('unavailable', interface)

    def profiles(self):
        profiles = []
        for line in self.query('UUID,NAME,TYPE', 'connection', 'show').splitlines():
            uuid, name, kind = fields(line, 3)
            if kind not in ('wifi', '802-11-wireless'):
                continue
            if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', uuid):
                raise ValueError('invalid profile UUID')
            profiles.append((uuid, name))
        # No secret fields requested; UUIDs, never display names, identify actions.
        return profiles

    def profile_ssid(self, uuid):
        output = self.runner(['nmcli', '-t', '-e', 'yes', '-g', '802-11-wireless.ssid',
                              'connection', 'show', 'uuid', uuid], timeout=2).stdout.strip('\n')
        return fields(output, 1)[0]

    def action(self, *args, timeout=12):
        return self.runner(['nmcli', '--wait', '10' if timeout <= 12 else '40',
                            *args], timeout=timeout)


@dataclass(frozen=True)
class Choice:
    text: str
    action: str
    args: tuple = ()


def menu_choices(nm):
    enabled = nm.radio()
    devices = nm.devices()
    interface = devices[0][0] if devices else ''
    choices = []
    profiles = nm.profiles()
    by_ssid = {}
    for uuid, name in profiles:
        try:
            by_ssid.setdefault(nm.profile_ssid(uuid), uuid)
        except (CommandError, ValueError):
            pass
    if enabled and interface:
        points = nm.access_points(interface)
        for ap in sorted(points, key=lambda ap: (not ap.active, -(ap.signal or 0), ap.ssid, ap.bssid)):
            security = ap.security if ap.security not in ('', '--') else 'open'
            strength = f'{ap.signal}%' if ap.signal is not None else '?'
            prefix = 'Connected' if ap.active else 'Network'
            uuid = by_ssid.get(ap.ssid)
            suffix = 'saved' if uuid else 'configure in editor'
            text = f'{prefix}: {label(ap.ssid or "hidden")} | {strength} | {label(security)} | {suffix}'
            choices.append(Choice(text, 'activate' if uuid else 'new',
                                  (uuid, interface, ap.bssid) if uuid else ()))
        if any(ap.active for ap in points):
            choices.append(Choice('Disconnect', 'disconnect', (interface,)))
        choices.append(Choice('Refresh networks', 'refresh', (interface,)))
    for uuid, name in profiles:
        choices.append(Choice(f'Saved: {label(name)}', 'saved', (uuid, interface)))
    choices.append(Choice('Disable Wi-Fi' if enabled else 'Enable Wi-Fi',
                          'radio', ('off' if enabled else 'on',)))
    choices.append(Choice('Connection settings', 'settings'))
    return choices


def perform(nm, choice, runner=run):
    if choice.action in ('activate', 'saved'):
        uuid, interface, *bssid = choice.args
        args = ['connection', 'up', 'uuid', uuid]
        if interface:
            args += ['ifname', interface]
        if bssid:
            args += ['ap', bssid[0]]
        nm.action(*args, timeout=45)
    elif choice.action == 'disconnect':
        nm.action('device', 'disconnect', choice.args[0])
    elif choice.action == 'refresh':
        nm.action('device', 'wifi', 'rescan', 'ifname', choice.args[0])
    elif choice.action == 'radio':
        nm.action('radio', 'wifi', choice.args[0])
    elif choice.action in ('settings', 'new', 'edit'):
        args = ['nm-connection-editor']
        if choice.action == 'new':
            args += ['--create', '--type=802-11-wireless']
        elif choice.action == 'edit':
            args += ['--edit=' + choice.args[0]]
        runner(args, timeout=300)
    else:
        raise ValueError('unknown menu action')
