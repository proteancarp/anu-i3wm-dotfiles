"""Real 2.3.0 renderer/state fixtures and read-only preview protocol test.

Run: ~/.local/share/venvs/bumblebee-status/bin/python -B tests/validate_powerline.py
All simulated controls run against mocks; all artifacts live in temporary storage.
"""

import contextlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VENV = Path(sys.prefix)
ORDER = ['mm_audio', 'mm_wifi', 'battery', 'date', 'clock']
WIDGET_ORDER = ['volume', 'mute', 'mm_wifi', 'battery', 'date', 'clock']


def content_name(block):
    if block['name'] == 'mm_audio':
        return 'volume' if block['instance'].endswith('::0') else 'mute'
    return block['name']


def fixtures():
    assert importlib.metadata.version('bumblebee-status') == '2.3.0'
    with tempfile.TemporaryDirectory(prefix='mountain-mist-theme-fixtures-') as tmp:
        home = Path(tmp)
        (home / '.config').mkdir()
        (home / '.config/bumblebee-status').symlink_to(ROOT / '.config/bumblebee-status')
        with patch.dict(os.environ, HOME=tmp, XDG_DATA_DIRS=str(VENV / 'share')):
            import bumblebee_status.discover
            bumblebee_status.discover.discover()
            import core.config
            import core.event
            import core.input
            import core.module
            import core.output
            import core.theme
            import modules.contrib.battery as battery
            assert 'mountain-mist-powerline' in core.theme.themes()
            core.event.clear()
            config = core.config.Config([
                '-c', str(ROOT / '.config/bumblebee-status/config'),
                '-t', 'mountain-mist-powerline', '-p', 'battery.device=BAT0'])
            assert config.get('battery.warning') == '21'
            assert config.get('battery.critical') == '11'
            theme = core.theme.Theme('mountain-mist-powerline')
            output = core.output.i3(theme, config)
            modules = [core.module.load(name, config, theme) for name in config.modules()]
            assert [m.id for m in modules] == ORDER
            for m in modules:
                m.background = False  # deterministic synchronous fixture updates
                m.register_callbacks()
            output.modules(modules)
            audio, wifi, bat, _, _ = modules
            fixture_count = 0
            assert output.start()['blocks'] == {'version': 1, 'click_events': True}

            def render(volume='Volume: 1.00', wifi_state='connected', charge='Discharging', capacity=74):
                nonlocal fixture_count
                fixture_count += 1
                nm_wifi = sys.modules['modules.mm_wifi']
                nm_audio = sys.modules['modules.mm_audio']
                link = nm_wifi.Wifi(wifi_state, 'wlan-test', 'Example WiFi', 57)
                with patch.object(nm_audio, 'run', return_value=subprocess.CompletedProcess([], 0, volume, '')) as query, \
                     patch.object(nm_wifi, 'NetworkManager') as manager, \
                     patch.object(battery.BatteryManager, 'capacity', return_value=capacity), \
                     patch.object(battery.BatteryManager, 'isac_any', return_value=False), \
                     patch.object(battery.BatteryManager, 'charge', return_value=charge), \
                     patch.object(battery.BatteryManager, 'charge_any', return_value=charge):
                    manager.return_value.status.return_value = link
                    output.update(force=True)
                    assert query.call_count == 1, 'two audio widgets must share one acquisition'
                    capture = io.StringIO()
                    with contextlib.redirect_stdout(capture):
                        core.event.trigger('draw')  # render once with reset transition colors
                    frame = json.loads(capture.getvalue().strip().rstrip(','))
                json.loads(json.dumps(frame))
                assert len(frame) == 12
                assert [content_name(b) for b in frame[1::2]] == WIDGET_ORDER
                for i in range(0, len(frame), 2):
                    arrow, content = frame[i:i+2]
                    assert arrow['full_text'] == '\ue0b2'
                    assert arrow['color'] == content['background']
                    assert arrow['background'] == (frame[i-1]['background'] if i else None), (i, arrow, frame)
                    assert arrow['separator'] is False and content['separator'] is False
                    assert arrow['separator_block_width'] == content['separator_block_width'] == 0
                    assert arrow['instance'] == content['instance']
                    assert '|' not in content['full_text']
                    assert not any(0xf000 <= ord(c) <= 0xf8ff for c in content['full_text'])
                return {content_name(b): b for b in frame[1::2]}

            def color(block, fg, bg):
                assert (block['color'], block['background']) == (fg, bg), block

            # Renderer emits frames when fixture update/draw events fire. Keep stdout
            # exclusively for the final fixture result, not hundreds of JSON lines.
            with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink):
                normal = render()
                color(normal['volume'], '#e0e6e7', '#46565b')
                color(normal['mute'], '#c8d1d5', '#182326')
                color(normal['mm_wifi'], '#11191c', '#6f9291')
                color(normal['battery'], '#8aa3a5', '#182326')
                color(normal['date'], '#c8d1d5', '#182124')
                color(normal['clock'], '#e0e6e7', '#11191c')
                assert normal['volume']['full_text'].strip() == 'VOL 100%'
                assert normal['mute']['full_text'].strip() == 'MUTE'
                assert normal['mm_wifi']['full_text'].strip() == 'WiFi Example WiFi 57%'
                assert normal['battery']['full_text'].strip() == 'BAT 74%'
                assert normal['date']['full_text'].strip()
                assert ':' in normal['clock']['full_text']
                muted = render(volume='Volume: 0.80 [MUTED]')
                color(muted['mute'], '#657f91', '#182124')
                color(muted['volume'], '#e0e6e7', '#46565b')
                assert muted['volume']['full_text'].strip() == 'VOL 80%'
                assert muted['mute']['full_text'].strip() == 'MUTED'
                unavailable = render(volume='invalid')
                for name in ('volume', 'mute'):
                    color(unavailable[name], '#11191c', '#9b6b6b')
                color(render(wifi_state='disconnected')['mm_wifi'], '#c8d1d5', '#46565b')
                color(render(wifi_state='disabled')['mm_wifi'], '#657f91', '#182124')
                color(render(wifi_state='unavailable')['mm_wifi'], '#11191c', '#9b6b6b')
                color(render(wifi_state='connecting')['mm_wifi'], '#a39a76', '#182326')
                color(render(charge='Charging')['battery'], '#11191c', '#6f9291')
                color(render(charge='Full', capacity=100)['battery'], '#11191c', '#6f9291')
                healthy = render(capacity=21)['battery']
                color(healthy, '#8aa3a5', '#182326')
                assert healthy['full_text'].strip() == 'BAT 21%'
                for value in (20, 19, 18, 11):
                    low = render(capacity=value)['battery']
                    color(low, '#11191c', '#a39a76')
                    assert low['full_text'].strip() == f'BAT {value}% LOW'
                for value in (10, 9, 8, 5, 0):
                    critical = render(capacity=value)['battery']
                    color(critical, '#11191c', '#b77d7d')
                    assert critical['full_text'].strip() == f'BAT {value}% CRIT'
                color(render(charge='Unknown', capacity=-1)['battery'], '#b77d7d', '#24191b')
                # Existing handlers still register and invoke their existing commands;
                # theme separator/content IDs point to the same widget.
                with patch.object(sys.modules['modules.mm_audio'], 'run') as controls:
                    with patch('util.cli.execute') as global_action:
                        core.input.register(None, core.input.WHEEL_UP, 'i3-msg workspace prev_on_output')
                        core.input.register(None, core.input.WHEEL_DOWN, 'i3-msg workspace next_on_output')
                        core.input.trigger(dict(normal['volume'], button=1))
                        for button in (4, 5):
                            core.input.trigger(dict(normal['mute'], button=button))
                        controls.assert_not_called()
                        global_action.assert_not_called()
                        for button in (4, 5):
                            core.input.trigger(dict(normal['volume'], button=button))
                        core.input.trigger(dict(normal['mute'], button=1))
                    assert [c.args[0] for c in controls.call_args_list] == [
                        ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%+'],
                        ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%-'],
                        ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle']]
                    assert all(c.kwargs['timeout'] == 2 for c in controls.call_args_list)
                with patch.object(sys.modules['modules.mm_wifi'], 'start_helper') as helper:
                    core.input.trigger(dict(normal['mm_wifi'], button=1))
                    helper.assert_called_once_with('rofi-network')
                with patch('util.cli.execute') as command:
                    for name in ('date', 'clock'):
                        core.input.trigger(dict(normal[name], button=1))
                    assert command.call_count == 2
                    assert all('rofi-calendar' in c.args[0] for c in command.call_args_list)
    print(f'PASS: named staged theme discovery, {fixture_count} state/boundary frames, all transitions, native LOW/CRIT suffixes, shared audio query and independent click targets')


FAKE = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['MM_PREVIEW_COMMAND_LOG'], 'a') as log:
    log.write(json.dumps([Path(sys.argv[0]).name, args]) + '\\n')
if Path(sys.argv[0]).name == 'wpctl':
    assert args == ['get-volume', '@DEFAULT_AUDIO_SINK@']
    print('Volume: 1.00')
elif args[-2:] == ['radio', 'wifi']:
    print('enabled')
elif args[-2:] == ['device', 'status']:
    print('wlan-test:wifi:connected')
elif 'IN-USE,SSID,SIGNAL,SECURITY,BSSID' in args:
    assert args[args.index('--rescan') + 1] == 'no'
    print('*:Example WiFi:57:WPA2:' + 'AA:BB:CC:DD:EE:FF'.replace(':', chr(92) + ':'))
else:
    raise SystemExit('unexpected command: read-only preview failed')
'''


def preview_protocol():
    with tempfile.TemporaryDirectory(prefix='mountain-mist-preview-protocol-') as tmp:
        lab = Path(tmp)
        fake = lab / 'fake-command'
        fake.write_text(FAKE)
        fake.chmod(0o755)
        for name in ('wpctl', 'nmcli'):
            (lab / name).symlink_to(fake)
        env = os.environ.copy()
        env.update(PATH=f'{lab}:{env.get("PATH", "")}', MM_PREVIEW_COMMAND_LOG=str(lab / 'commands.jsonl'),
                   PYTHONDONTWRITEBYTECODE='1')
        proc = subprocess.Popen([str(ROOT / 'scripts/preview-powerline-status')], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=env, start_new_session=True)
        lines = queue.Queue()
        errors = []
        def read_stdout():
            for line in proc.stdout:
                lines.put(line)
        def read_stderr():
            errors.extend(proc.stderr.readlines())
        readers = [threading.Thread(target=read_stdout, daemon=True),
                   threading.Thread(target=read_stderr, daemon=True)]
        for reader in readers:
            reader.start()
        frames = []
        try:
            assert json.loads(lines.get(timeout=10)) == {'version': 1, 'click_events': True}
            proc.stdin.write('[\n')
            proc.stdin.flush()
            started = time.monotonic()
            end = started + 17
            while time.monotonic() < end:
                try:
                    line = lines.get(timeout=max(.1, end - time.monotonic())).strip()
                except queue.Empty:
                    raise AssertionError((proc.poll(), len(frames), frames[-1:] , errors))
                if not line or line == '[':
                    continue
                frame = json.loads(line.rstrip(','))
                assert len(frame) == 12
                assert [content_name(b) for b in frame if not b.get('_decorator')] == WIDGET_ORDER
                frames.append(frame)
                contents = {content_name(b): b for b in frame if not b.get('_decorator')}
                if time.monotonic() - started >= 10 and len(frames) >= 3 and \
                        'VOL 100%' in contents['volume']['full_text'] and \
                        'Example WiFi 57%' in contents['mm_wifi']['full_text']:
                    # Delivery is disabled in the preview, not in production modules.
                    for name in ('volume', 'mute', 'mm_wifi', 'date', 'clock'):
                        proc.stdin.write(',' + json.dumps(dict(contents[name], button=1)) + '\n')
                    proc.stdin.flush()
                    time.sleep(.3)
                    break
            else:
                raise AssertionError('preview modules did not resolve')
            assert proc.poll() is None and not proc.stdin.closed
            assert len(frames) < 30, 'redraw storm'
            proc.send_signal(signal.SIGTERM)
            assert proc.wait(timeout=5) == 0
            for reader in readers:
                reader.join(timeout=2)
            assert not errors, ''.join(errors)
            commands = [json.loads(line) for line in (lab / 'commands.jsonl').read_text().splitlines()]
            assert all('--wait' not in args and 'rescan' not in args for _, args in commands)
            assert all(tool in ('wpctl', 'nmcli') for tool, _ in commands)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()
    print(f'PASS: staged preview, production venv, open stdin, {len(frames)} frames, valid JSON, click_events, no controls and clean termination')


if __name__ == '__main__':
    fixtures()
    preview_protocol()
