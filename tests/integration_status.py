"""Validate with a caller-provided 2.3.0 venv; never install or use live tools.

Usage: python3 -B tests/integration_status.py PATH_TO_VENV
All temporary HOME/config/command artifacts are created and removed in the repo.
"""

import json
import os
from pathlib import Path
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]

BATTERY_CHECK = '''
import os
from pathlib import Path
from unittest.mock import patch
import bumblebee_status.discover
bumblebee_status.discover.discover()
import core.config, core.output, core.theme
import modules.contrib.battery as battery
root = Path(os.environ['MM_REPO_ROOT'])
config = core.config.Config(['-c', str(root / '.config/bumblebee-status/config')])
# Also exercise named user-theme discovery, not only launcher's absolute -t.
theme = core.theme.Theme('mountain-mist-powerline')
module = battery.Module(config, theme)
output = core.output.i3(theme, config)
output.modules([module])
cases = [('Discharging', 21, '#8aa3a5', '#182326', 'BAT 21%'),
         ('Discharging', 20, '#11191c', '#a39a76', 'BAT 20% LOW'),
         ('Discharging', 11, '#11191c', '#a39a76', 'BAT 11% LOW'),
         ('Discharging', 10, '#11191c', '#b77d7d', 'BAT 10% CRIT'),
         ('Discharging', 5, '#11191c', '#b77d7d', 'BAT 5% CRIT'),
         ('Charging', 92, '#11191c', '#6f9291', 'BAT 92%'),
         ('Full', 100, '#11191c', '#6f9291', 'BAT 100%')]
for charge, capacity, color, background, text in cases:
    with patch.object(battery.BatteryManager, 'capacity', return_value=capacity), \\
         patch.object(battery.BatteryManager, 'isac_any', return_value=False), \\
         patch.object(battery.BatteryManager, 'charge', return_value=charge), \\
         patch.object(battery.BatteryManager, 'charge_any', return_value=charge):
        output.update(force=True)
        block = output.statusline()['blocks'][1].dict()
        assert block['color'] == color, block
        assert block['background'] == background, block
        assert text in block['full_text'], block
print('Battery full-segment/suffix fixtures: PASS (7 states, including exact boundaries)')
'''

FAKE = r'''#!/usr/bin/python3
import json, os
from pathlib import Path
import sys, time
root = Path(os.environ['MM_TEST_ROOT'])
tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with (root/'commands.jsonl').open('a') as log:
    log.write(json.dumps([tool, args])+'\n')
state = json.loads((root/'state.json').read_text())
def esc(s): return str(s).replace('\\','\\\\').replace(':','\\:')
def row(*s): print(':'.join(map(esc,s)))
if tool == 'wpctl':
    mode = state['audio']
    if mode == 'timeout': time.sleep(20)
    if mode == 'failure': sys.exit(1)
    if args[0] == 'get-volume':
        print('Volume: 0.42 [MUTED]' if mode == 'muted' else 'Volume: 0.42')
elif tool == 'nmcli':
    mode = state['wifi']
    if mode == 'timeout': time.sleep(20)
    if mode == 'failure': sys.exit(1)
    if args[-2:] == ['radio','wifi']: print('disabled' if mode == 'disabled' else 'enabled')
    elif args[-2:] == ['device','status']:
        row('wlan-test','wifi','connecting (prepare)' if mode == 'connecting' else 'disconnected' if mode == 'disconnected' else 'connected')
    elif 'IN-USE,SSID,SIGNAL,SECURITY,BSSID' in args:
        row('*',r'Home:Lab\SSID',82,'WPA2','AA:BB:CC:DD:EE:FF')
elif tool in ('rofi-network','rofi-calendar'):
    assert sys.stdin.read() == ''
else:
    raise SystemExit('unexpected fake tool')
'''


def main(venv):
    with tempfile.TemporaryDirectory(prefix='.status-integration-', dir=ROOT) as temp:
        lab = Path(temp)
        home = lab / 'home'
        (home / '.config').mkdir(parents=True)
        (home / '.local/bin').mkdir(parents=True)
        (home / '.local/share/venvs').mkdir(parents=True)
        (home / '.local/share/venvs/bumblebee-status').symlink_to(venv)
        (home / '.local/lib').symlink_to(ROOT / '.local/lib')
        (home / '.config/bumblebee-status').symlink_to(ROOT / '.config/bumblebee-status')
        (home / '.config/rofi').symlink_to(ROOT / '.config/rofi')
        fakebin = lab / 'bin'
        fakebin.mkdir()
        fake = lab / 'fake-command'
        fake.write_text(FAKE)
        fake.chmod(0o755)
        for name in ('wpctl', 'nmcli'):
            (fakebin / name).symlink_to(fake)
        for name in ('rofi-network', 'rofi-calendar'):
            # argv[0] is the symlink name; no real desktop helper executes.
            (home / '.local/bin' / name).symlink_to(fake)
        state = {'audio':'normal', 'wifi':'connected'}
        state_file = lab / 'state.json'
        def set_state(**changes):
            state.update(changes)
            staged = lab / 'state.new'
            staged.write_text(json.dumps(state))
            staged.replace(state_file)
        set_state()
        env = os.environ.copy()
        env.update(HOME=str(home), PATH=str(fakebin), MM_TEST_ROOT=str(lab),
                   XDG_DATA_DIRS='/existing/data', XDG_RUNTIME_DIR=str(lab),
                   PYTHONDONTWRITEBYTECODE='1')
        for key in ('DISPLAY','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','PULSE_SERVER'):
            env.pop(key, None)
        # The optional command socket is separate from the i3bar stdin protocol.
        # When this sandbox denies binds, isolate only that unused listener in
        # the test process; all production stdin/render/control code stays real.
        command_socket_available = True
        probe = lab / 'socket-probe'
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(probe))
        except PermissionError:
            command_socket_available = False
            (lab / 'sitecustomize.py').write_text(
                'import threading\n'
                '_start = threading.Thread.start\n'
                'def start(self):\n'
                '    if getattr(getattr(self, "_target", None), "__name__", "") == "handle_commands":\n'
                '        return\n'
                '    return _start(self)\n'
                'threading.Thread.start = start\n')
            env['PYTHONPATH'] = str(lab) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        finally:
            probe.unlink(missing_ok=True)
        fixture_env = dict(env, XDG_DATA_DIRS=str(venv / 'share'), MM_REPO_ROOT=str(ROOT))
        fixture = subprocess.run([str(venv / 'bin/python'), '-B', '-c', BATTERY_CHECK],
                                 env=fixture_env, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=10)
        assert fixture.returncode == 0, fixture.stderr
        print(fixture.stdout.strip(), flush=True)
        # /usr/bin/bash is explicit because PATH has only fake commands.
        proc = subprocess.Popen(['/usr/bin/bash', str(ROOT / '.local/bin/mountain-mist-status')],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=env, start_new_session=True)
        socket_path = Path(f'/tmp/.bumblebee-status.{proc.pid}')
        lines = queue.Queue()
        capture, errors = [], []
        def read_output():
            for line in proc.stdout:
                capture.append(line)
                lines.put(line)
        def read_errors():
            for line in proc.stderr:
                errors.append(line)
        reader = threading.Thread(target=read_output, daemon=True)
        err_reader = threading.Thread(target=read_errors, daemon=True)
        reader.start(); err_reader.start()
        def next_frame(timeout=6):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                line = lines.get(timeout=max(.01, deadline-time.monotonic())).strip()
                if line == '[':
                    continue
                return json.loads(line.rstrip(','))
            raise AssertionError('no frame')
        def until(predicate, timeout=8):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                frame = next_frame(max(.01, deadline - time.monotonic()))
                if predicate(frame):
                    return frame
            raise AssertionError('expected frame not produced')
        def block(frame, name, widget_index=0):
            return [b for b in frame if b['name'] == name and not b.get('_decorator')][widget_index]
        def click(frame, name, button=1, widget_index=0):
            event = {'name':name, 'instance':block(frame,name,widget_index)['instance'], 'button':button}
            proc.stdin.write(',' + json.dumps(event) + '\n')
            proc.stdin.flush()
        def cpu():
            values = Path(f'/proc/{proc.pid}/stat').read_text().split()
            return (int(values[13]) + int(values[14])) / os.sysconf('SC_CLK_TCK')
        try:
            header = json.loads(lines.get(timeout=8))
            assert header == {'version':1, 'click_events':True}, header
            proc.stdin.write('[\n'); proc.stdin.flush()
            frame = until(lambda f:'VOL 42%' in block(f,'mm_audio')['full_text'] and
                          '82%' in block(f,'mm_wifi')['full_text'])
            assert len(frame) == 12
            assert [b['name'] for b in frame if not b.get('_decorator')] == ['mm_audio','mm_audio','mm_wifi','battery','date','clock'], frame
            assert block(frame,'mm_audio')['background'] == '#46565b'
            assert block(frame,'mm_audio',1)['full_text'].strip() == 'MUTE'
            assert block(frame,'mm_audio')['instance'] != block(frame,'mm_audio',1)['instance']
            assert block(frame,'mm_wifi')['background'] == '#6f9291'
            assert 'BAT' in block(frame,'battery')['full_text']
            assert all('error' not in b['full_text'].lower() for b in frame)
            print('Initial frame:', json.dumps(frame), flush=True)
            process_env = Path(f'/proc/{proc.pid}/environ').read_bytes().split(b'\0')
            expected = f'XDG_DATA_DIRS={home}/.local/share/venvs/bumblebee-status/share:/existing/data'.encode()
            assert expected in process_env
            assert not proc.stdin.closed
            assert b'battery.device=' in Path(f'/proc/{proc.pid}/cmdline').read_bytes()
            # All synthetic callbacks invoke only controlled command fakes.
            click(frame,'mm_audio',1)
            for button in (4,5): click(frame,'mm_audio',button,1)
            time.sleep(.3)
            commands = [json.loads(line) for line in (lab/'commands.jsonl').read_text().splitlines()]
            assert not any(tool=='wpctl' and args[0].startswith('set-') for tool,args in commands)
            for button in (4,5): click(frame,'mm_audio',button)
            click(frame,'mm_audio',1,1)
            click(frame,'mm_wifi')
            click(frame,'date')
            deadline = time.monotonic() + 8
            while True:
                commands = [json.loads(line) for line in (lab/'commands.jsonl').read_text().splitlines()]
                if sum(tool=='wpctl' and args[0]=='set-volume' for tool,args in commands)==2 and \
                        {'rofi-network','rofi-calendar'} <= {tool for tool,_ in commands}:
                    break
                if time.monotonic() >= deadline:
                    raise AssertionError(('click commands missing', commands, errors))
                time.sleep(.05)
            assert any(tool=='wpctl' and args[0]=='set-mute' for tool,args in commands)
            volumes = [args for tool,args in commands if tool=='wpctl' and args[0]=='set-volume']
            assert all('--limit' in args and '1.0' in args for args in volumes) and len(volumes)==2, volumes
            assert {'rofi-network','rofi-calendar'} <= {tool for tool,_ in commands}
            set_state(audio='muted',wifi='disabled')
            click(frame,'mm_audio',-1);click(frame,'mm_wifi',-1)
            frame = until(lambda f:block(f,'mm_audio',1)['full_text'].strip()=='MUTED' and
                          'WiFi off' in block(f,'mm_wifi')['full_text'])
            assert block(frame,'mm_audio')['full_text'].strip()=='VOL 42%'
            assert block(frame,'mm_audio',1)['color']=='#657f91'
            assert block(frame,'mm_wifi')['color']=='#657f91'
            set_state(audio='timeout',wifi='timeout')
            # UPDATE=-1 bypasses action bindings while requesting forced refresh.
            click(frame,'mm_audio',-1);click(frame,'mm_wifi',-1)
            frame = until(lambda f:'VOL ?' in block(f,'mm_audio')['full_text'] and
                          'WiFi ?' in block(f,'mm_wifi')['full_text'], timeout=9)
            assert block(frame,'mm_audio',1)['full_text'].strip() == 'MUTE ?'
            assert proc.poll() is None
            set_state(audio='failure',wifi='failure')
            click(frame,'mm_audio',-1);click(frame,'mm_wifi',-1)
            time.sleep(.5)
            set_state(audio='normal',wifi='connected')
            click(frame,'mm_audio',-1);click(frame,'mm_wifi',-1)
            frame = until(lambda f:'VOL 42%' in block(f,'mm_audio')['full_text'] and
                          '82%' in block(f,'mm_wifi')['full_text'])
            before = cpu(); started = time.monotonic()
            # Long enough for repeated ordinary 15-second Wi-Fi polling cycles.
            time.sleep(31)
            elapsed = time.monotonic()-started
            used = cpu()-before
            snapshot = {}
            for line in Path(f'/proc/{proc.pid}/smaps_rollup').read_text().splitlines():
                if line.startswith(('Rss:', 'Pss:')):
                    key,value,*_ = line.split()
                    snapshot[key.rstrip(':')+'_KiB'] = int(value)
            assert proc.poll() is None and not proc.stdin.closed
            frames = [json.loads(line.strip().rstrip(',')) for line in capture[2:]]
            assert len(frames)<150, 'redraw storm with open stdin'
            commands = [json.loads(line) for line in (lab/'commands.jsonl').read_text().splitlines()]
            assert sum(tool=='nmcli' and args[-2:]==['radio','wifi'] for tool,args in commands)>=5
            assert all('--rescan' not in args or 'no' in args for tool,args in commands if tool=='nmcli')
            snapshot.update(cpu_seconds=round(used,3), duration_seconds=round(elapsed,3),
                            one_core_cpu_percent=round(used/elapsed*100,2),
                            frames_total=len(frames), stderr=''.join(errors),
                            command_socket='enabled' if command_socket_available else 'SKIPPED: sandbox denies Unix socket bind; stdin controls fully exercised',
                            integration='PASS: real 2.3.0, staged launcher/config/theme/modules, fake tools, synthetic events, timeout/failure recovery, open stdin')
            print(json.dumps(snapshot, indent=2), flush=True)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=2)
            proc.stdin.close()
            reader.join(timeout=2); err_reader.join(timeout=2)
            socket_path.unlink(missing_ok=True)
            proc.stdout.close(); proc.stderr.close()
            assert not errors, ''.join(errors)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]).resolve())
