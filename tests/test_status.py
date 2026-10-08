"""Run with python3 -B -m unittest discover -s tests -v; no desktop commands."""

from datetime import date
import importlib.util
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/lib'))
from mountain_mist import calendar_view, network, runtime

UUID = '12345678-1234-1234-1234-123456789abc'
SSID = r'Home: lab\name $(touch SHOULD_NOT_EXIST); "x"'


def escape(value):
    return value.replace('\\', '\\\\').replace(':', '\\:')


def row(*values):
    return ':'.join(escape(str(value)) for value in values) + '\n'


def result(text='', code=0):
    return subprocess.CompletedProcess([], code, text, '')


class FakeNM:
    def __init__(self):
        self.enabled = True
        self.state = 'connected'
        self.has_device = True
        self.ssid = SSID
        self.calls = []
        self.failure = None

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if self.failure:
            raise self.failure
        if argv[-2:] == ['radio', 'wifi']:
            return result('enabled\n' if self.enabled else 'disabled\n')
        if argv[-2:] == ['device', 'status']:
            return result(row('wlan-test', 'wifi', self.state) if self.has_device else row('lo', 'loopback', 'connected'))
        if 'IN-USE,SSID,SIGNAL,SECURITY,BSSID' in argv:
            return result(row('*' if self.state == 'connected' else '', self.ssid, 82, 'WPA2', 'AA:BB:CC:DD:EE:FF'))
        if argv[-2:] == ['connection', 'show']:
            return result(row(UUID, 'Saved:name\\test', '802-11-wireless'))
        if '802-11-wireless.ssid' in argv:
            return result(escape(self.ssid) + '\n')
        if 'radio' in argv:
            self.enabled = argv[-1] == 'on'
        return result()


# Unit tests do not require Bumblebee installed. The integration suite checks
# these same modules against the real pinned API rather than this small scaffold.
class Base:
    def __init__(self, config, theme, widgets):
        self.id = self.__module__
        self.params = {}
        self.items = widgets

    def add_widget(self, text, name=None):
        widget = types.SimpleNamespace(id=f'{self.id}::{len(self.items)}', name=name)
        self.items.append(widget)
        return widget

    def set(self, key, value):
        self.params[key] = value

    def parameter(self, key, default=None):
        return self.params.get(key, default)


def load_module(name):
    core = types.ModuleType('core')
    module = types.ModuleType('core.module')
    module.Module = Base
    inputs = types.ModuleType('core.input')
    inputs.LEFT_MOUSE, inputs.WHEEL_UP, inputs.WHEEL_DOWN = 1, 4, 5
    inputs.register = lambda *args: None
    core.module, core.input = module, inputs
    with patch.dict(sys.modules, {'core': core, 'core.module': module, 'core.input': inputs}):
        spec = importlib.util.spec_from_file_location(name, ROOT / '.config/bumblebee-status/modules' / (name + '.py'))
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
    return loaded


audio = load_module('mm_audio')
wifi = load_module('mm_wifi')
rofi_network = types.SimpleNamespace(**runpy.run_path(str(ROOT / '.local/bin/rofi-network'), run_name='test_network'))
rofi_calendar = types.SimpleNamespace(**runpy.run_path(str(ROOT / '.local/bin/rofi-calendar'), run_name='test_calendar'))


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.module = audio.Module(None, None)

    def update(self, value):
        with patch.object(audio, 'run', return_value=result(value)) as call:
            self.module.update()
        self.assertEqual(call.call_args.args[0], ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'])
        self.assertEqual(call.call_args.kwargs['timeout'], 2)

    def test_normal(self):
        self.update('Volume: 0.42\n')
        self.assertEqual(self.module.full_text(None), 'VOL 42%')

    def test_muted(self):
        self.update('Volume: 0.42 [MUTED]\n')
        self.assertEqual(self.module.full_text(self.module.volume), 'VOL 42%')
        self.assertEqual(self.module.full_text(self.module.mute), 'MUTED')
        self.assertEqual(self.module.state(self.module.volume), ['volume', 'normal'])
        self.assertEqual(self.module.state(self.module.mute), ['mute', 'muted'])

    def test_shared_snapshot_has_one_query_for_both_widgets(self):
        with patch.object(audio, 'run', return_value=result('Volume: 0.80')) as call:
            self.module.update()
            self.assertEqual(self.module.full_text(self.module.volume), 'VOL 80%')
            self.assertEqual(self.module.full_text(self.module.mute), 'MUTE')
            self.assertEqual(self.module.state(self.module.mute), ['mute', 'normal'])
            self.assertEqual(call.call_count, 1)

    def test_widget_clicks_are_separate(self):
        bindings = {}
        with patch.object(audio.core.input, 'register',
                          side_effect=lambda obj, button, cmd: bindings.update({(obj.id, button): cmd})):
            module = audio.Module(None, None)
        with patch.object(audio, 'run', return_value=result()) as call:
            bindings[(module.volume.id, 1)]({})
            bindings[(module.mute.id, 4)]({})
            bindings[(module.mute.id, 5)]({})
            call.assert_not_called()
            bindings[(module.volume.id, 4)]({})
            bindings[(module.volume.id, 5)]({})
            bindings[(module.mute.id, 1)]({})
        self.assertEqual([c.args[0] for c in call.call_args_list], [
            ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%+'],
            ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%-'],
            ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'],
        ])
        self.assertTrue(all(c.kwargs['timeout'] == 2 for c in call.call_args_list))
        self.assertEqual(len(bindings), 6)

    def test_malformed(self):
        for output in ('', 'oops', 'Volume: nan', 'Volume: -1', 'Volume: 0.2 garbage', 'Volume: 9999', 'Volume: 0.1\nVolume: 0.2'):
            with self.subTest(output=output):
                self.update(output)
                self.assertEqual(self.module.full_text(None), 'VOL ?')

    def test_rounding(self):
        self.assertEqual(audio.parse_volume('Volume: 0.425'), (43, False))

    def test_over_100_reading_does_not_hide_existing_amplification(self):
        self.update('Volume: 1.25')
        self.assertEqual(self.module.full_text(None), 'VOL 125%')

    def test_timeout_and_failure_recover(self):
        for reason in ('wpctl: timed out', 'wpctl: failed (1)'):
            with patch.object(audio, 'run', side_effect=runtime.CommandError(reason)):
                self.module.update()
            self.assertEqual(self.module.full_text(None), 'VOL ?')
            self.assertEqual(self.module.full_text(self.module.mute), 'MUTE ?')
            self.assertEqual(self.module.state(self.module.volume), ['volume', 'unavailable'])
            self.assertEqual(self.module.state(self.module.mute), ['mute', 'unavailable'])
        self.update('Volume: 0.42')
        self.assertEqual(self.module.full_text(None), 'VOL 42%')

    def test_ceiling_and_click_mappings(self):
        with patch.object(audio, 'run', return_value=result()) as call:
            self.module.toggle({})
            self.module.increase({})
            self.module.decrease({})
        self.assertEqual([c.args[0] for c in call.call_args_list], [
            ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'],
            ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%+'],
            ['wpctl', 'set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '2%-'],
        ])
        self.assertTrue(all(c.kwargs['timeout'] == 2 for c in call.call_args_list))

    def test_failed_click_does_not_raise(self):
        with patch.object(audio, 'run', side_effect=runtime.CommandError('wpctl: failed')):
            self.module.toggle({})
        self.assertEqual(self.module.full_text(None), 'VOL ?')
        self.assertEqual(self.module.full_text(self.module.mute), 'MUTE ?')

    def test_device_change_uses_default_token_every_time(self):
        self.update('Volume: 0.42')
        self.update('Volume: 0.17')
        self.assertEqual(self.module.full_text(None), 'VOL 17%')


class WifiTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeNM()
        self.nm = network.NetworkManager(self.fake)

    def test_connected_unusual_ssid(self):
        state = self.nm.status()
        self.assertEqual(state.ssid, SSID)
        self.assertTrue(state.text.endswith('82%'))
        self.assertLessEqual(len(state.text), 30)
        self.assertTrue(any('--rescan' in call[0] and 'no' in call[0] for call in self.fake.calls))
        self.assertFalse(any('connectivity' in call[0] for call in self.fake.calls))

    def test_disconnected(self):
        self.fake.state = 'disconnected'
        self.assertEqual(self.nm.status().text, 'WiFi down')

    def test_disabled(self):
        self.fake.enabled = False
        self.assertEqual(self.nm.status().text, 'WiFi off')
        self.assertEqual(len(self.fake.calls), 1)

    def test_connecting(self):
        self.fake.state = 'connecting (getting IP configuration)'
        self.assertEqual(self.nm.status().text, 'WiFi connecting')

    def test_missing_device(self):
        self.fake.has_device = False
        self.assertEqual(self.nm.status().text, 'WiFi ?')

    def test_connected_but_ap_vanished(self):
        with patch.object(self.nm, 'access_points', return_value=[]):
            self.assertEqual(self.nm.status().text, 'WiFi ?')

    def test_missing_signal(self):
        ap = network.AccessPoint('Home', None, 'WPA2', 'AA:BB:CC:DD:EE:FF', True)
        with patch.object(self.nm, 'access_points', return_value=[ap]):
            self.assertEqual(self.nm.status().text, 'WiFi Home')

    def test_escaping_and_malformed(self):
        self.assertEqual(network.fields(escape(SSID), 1), [SSID])
        for value, count in [('trailing\\', 1), ('x\\q', 1), ('a:b:c', 2)]:
            with self.assertRaises(ValueError):
                network.fields(value, count)

    def test_module_timeout_failure_malformed_recovery(self):
        m = wifi.Module(None, None)
        for failure in (runtime.CommandError('nmcli: timed out'), runtime.CommandError('nmcli: failed'), ValueError('invalid output')):
            with patch.object(wifi, 'NetworkManager') as factory:
                factory.return_value.status.side_effect = failure
                m.update()
            self.assertEqual(m.full_text(None), 'WiFi ?')
        with patch.object(wifi, 'NetworkManager') as factory:
            factory.return_value.status.return_value = network.Wifi('connected', 'wlan-test', 'Home', 82)
            m.update()
        self.assertEqual(m.full_text(None), 'WiFi Home 82%')

    def test_bad_signal_and_rows(self):
        for output in ('broken\n', row('*', 'Home', 200, 'WPA2', 'AA:BB:CC:DD:EE:FF'), row('*', 'Home', 'oops', 'WPA2', 'AA:BB:CC:DD:EE:FF')):
            with patch.object(self.nm, 'query', return_value=output):
                with self.assertRaises(ValueError):
                    self.nm.access_points('wlan-test')

    def test_multiple_adapters_prefers_connected(self):
        output = row('wlan0', 'wifi', 'disconnected') + row('wlan1', 'wifi', 'connected')
        with patch.object(self.nm, 'query', return_value=output):
            self.assertEqual(self.nm.devices()[0][0], 'wlan1')

    def test_helper_is_not_opened_twice(self):
        m = wifi.Module(None, None)
        with patch.object(wifi, 'start_helper') as launch:
            launch.return_value.poll.return_value = None
            m.open_menu({}); m.open_menu({})
            self.assertEqual(launch.call_count, 1)


class NetworkMenuTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeNM()
        self.nm = network.NetworkManager(self.fake)

    def test_safe_saved_activation(self):
        choices = network.menu_choices(self.nm)
        selected = next(c for c in choices if c.action == 'activate')
        network.perform(self.nm, selected)
        args = self.fake.calls[-1][0]
        self.assertIn(UUID, args)
        self.assertNotIn(SSID, args)
        self.assertEqual(args[-2:], ['ap', 'AA:BB:CC:DD:EE:FF'])
        self.assertNotIn('--ask', args)
        self.assertNotIn('password', args)

    def test_new_secured_network_delegates_editor(self):
        with patch.object(self.nm, 'profiles', return_value=[]):
            choice = next(c for c in network.menu_choices(self.nm) if c.action == 'new')
        with patch.object(network, 'run'):
            calls = []
            network.perform(self.nm, choice, runner=lambda args, **kw: calls.append(args))
        self.assertEqual(calls, [['nm-connection-editor', '--create', '--type=802-11-wireless']])

    def test_failed_or_vanished_activation(self):
        selected = next(c for c in network.menu_choices(self.nm) if c.action == 'activate')
        self.fake.failure = runtime.CommandError('nmcli: failed (10)')
        with self.assertRaises(runtime.CommandError):
            network.perform(self.nm, selected)

    def test_radio_transitions(self):
        choice = next(c for c in network.menu_choices(self.nm) if c.action == 'radio')
        network.perform(self.nm, choice)
        self.assertFalse(self.fake.enabled)
        choice = next(c for c in network.menu_choices(self.nm) if c.action == 'radio')
        network.perform(self.nm, choice)
        self.assertTrue(self.fake.enabled)

    def test_rescan_only_explicit_action(self):
        choices = network.menu_choices(self.nm)
        self.assertFalse(any('rescan' in argv for argv, _ in self.fake.calls))
        network.perform(self.nm, next(c for c in choices if c.action == 'refresh'))
        self.assertIn('rescan', self.fake.calls[-1][0])

    def test_menu_cancellation_does_not_mutate(self):
        main = rofi_network.main
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
             patch.dict(main.__globals__, {'helper_signals': lambda: None, 'NetworkManager': lambda *args: self.nm,
                                           'choose': lambda *args: None}):
            self.assertEqual(main(), 0)
        self.assertFalse(any('--wait' in argv for argv, _ in self.fake.calls))

    def test_failure_menu_cancels_cleanly(self):
        self.fake.failure = runtime.CommandError('nmcli: unavailable')
        main = rofi_network.main
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
             patch.dict(main.__globals__, {'helper_signals': lambda: None, 'NetworkManager': lambda *args: self.nm,
                                           'choose': lambda *args: None}):
            self.assertEqual(main(), 0)

    def test_close_exits_without_actions_in_all_menu_states(self):
        main = rofi_network.main
        for state in ('connected', 'disconnected', 'disabled', 'unavailable'):
            with self.subTest(state=state):
                fake = FakeNM()
                fake.state = 'disconnected' if state == 'disconnected' else 'connected'
                fake.enabled = state != 'disabled'
                if state == 'unavailable':
                    fake.failure = runtime.CommandError('nmcli: unavailable')
                nm = network.NetworkManager(fake)
                def close(rows, *args):
                    self.assertEqual(rows[-2:], ['Connection settings', 'Close'])
                    return len(rows) - 1
                with tempfile.TemporaryDirectory(dir=ROOT) as temp, \
                     patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
                     patch.dict(main.__globals__, {'helper_signals': lambda: None,
                                                   'NetworkManager': lambda *args: nm,
                                                   'choose': close}), \
                     patch.dict(main.__globals__, {'perform': unittest.mock.Mock()}) as globals_:
                    self.assertEqual(main(), 0)
                    globals_['perform'].assert_not_called()
                self.assertFalse(any('--wait' in argv or 'rescan' in argv
                                     for argv, _ in fake.calls))
                self.assertTrue(all('--rescan' not in argv or
                                    argv[argv.index('--rescan') + 1] == 'no'
                                    for argv, _ in fake.calls))

    def test_escape_returns_without_dispatching_actions(self):
        main = rofi_network.main
        for unavailable in (False, True):
            with self.subTest(unavailable=unavailable):
                if unavailable:
                    self.fake.failure = runtime.CommandError('nmcli: unavailable')
                def cancel(rows, prompt, theme, message, runner):
                    return runtime.choose(rows, prompt, theme, message,
                                          runner=lambda *args, **kwargs: result('', 1))
                with tempfile.TemporaryDirectory(dir=ROOT) as temp, \
                     patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
                     patch.dict(main.__globals__, {'helper_signals': lambda: None,
                                                   'NetworkManager': lambda *args: self.nm,
                                                   'choose': cancel}), \
                     patch.dict(main.__globals__, {'perform': unittest.mock.Mock()}) as globals_:
                    self.assertEqual(main(), 0)
                    globals_['perform'].assert_not_called()
                self.assertFalse(any('--wait' in argv or 'rescan' in argv
                                     for argv, _ in self.fake.calls))


class CalendarTests(unittest.TestCase):
    def test_launch_uses_calendar_layout_without_inputbar(self):
        main = rofi_calendar.main
        invocations = []
        def cancel(rows, prompt, theme, message, runner):
            def rofi(argv, **kwargs):
                invocations.append((argv, kwargs))
                return result('', 1)
            return runtime.choose(rows, prompt, theme, message, runner=rofi)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, \
             patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
             patch.dict(main.__globals__, {'helper_signals': lambda: None, 'choose': cancel}):
            self.assertEqual(main(), 0)
        self.assertEqual(len(invocations), 1)
        argv, kwargs = invocations[0]
        self.assertEqual(Path(argv[argv.index('-theme') + 1]).name, 'calendar.rasi')
        self.assertEqual(kwargs['input_text'].splitlines(),
                         ['Previous month', 'Next month', 'Today', 'Close'])
        self.assertIn('Mon Tue Wed Thu Fri Sat Sun', argv[argv.index('-mesg') + 1])
        theme = (ROOT / '.config/rofi/calendar.rasi').read_text()
        children = re.search(r'mainbox\s*\{[^}]*children:\s*\[([^]]+)\]', theme)
        self.assertIsNotNone(children)
        self.assertEqual([child.strip() for child in children.group(1).split(',')],
                         ['message', 'listview'])
        # The Wi-Fi layout must keep its useful search field.
        network_theme = (ROOT / '.config/rofi/network.rasi').read_text()
        children = re.search(r'mainbox\s*\{[^}]*children:\s*\[([^]]+)\]', network_theme)
        self.assertEqual([child.strip() for child in children.group(1).split(',')],
                         ['inputbar', 'message', 'listview'])

    def test_ordinary_month_and_monday_first(self):
        rendered = calendar_view.render(2026, 10, date(2026, 10, 7))
        self.assertIn('October 2026', rendered)
        self.assertIn('Mon Tue Wed Thu Fri Sat Sun', rendered)
        self.assertIn('[07]', rendered)
        self.assertIn(' 31 ', rendered)

    def test_december_to_january(self):
        self.assertEqual(calendar_view.move(2026, 12, 'Next month'), (2027, 1))

    def test_january_to_december(self):
        self.assertEqual(calendar_view.move(2026, 1, 'Previous month'), (2025, 12))

    def test_leap_year_february(self):
        self.assertIn(' 29 ', calendar_view.render(2024, 2, date(2024, 2, 1)))
        self.assertNotIn(' 29 ', calendar_view.render(2025, 2, date(2025, 2, 1)))

    def test_today_behavior(self):
        self.assertEqual(calendar_view.move(2025, 12, 'Today', date(2026, 10, 8)), (2026, 10))

    def test_year_bounds(self):
        self.assertEqual(calendar_view.move(1, 1, 'Previous month'), (1, 1))
        self.assertEqual(calendar_view.move(9999, 12, 'Next month'), (9999, 12))

    def test_escape(self):
        main = rofi_calendar.main
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}), \
             patch.dict(main.__globals__, {'helper_signals': lambda: None, 'choose': lambda *args: None}):
            self.assertEqual(main(), 0)


class RuntimeTests(unittest.TestCase):
    def test_real_timeout_is_bounded(self):
        start = time.monotonic()
        with self.assertRaises(runtime.CommandError):
            runtime.run([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=.1)
        self.assertLess(time.monotonic() - start, 1.5)

    def test_descendant_with_inherited_pipes_is_terminated(self):
        source = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c","import time; time.sleep(10)"])'
        start = time.monotonic()
        with self.assertRaises(runtime.CommandError):
            runtime.run([sys.executable, '-c', source], timeout=.1)
        self.assertLess(time.monotonic() - start, 1.5)

    def test_stdin_isolated(self):
        out = runtime.run([sys.executable, '-c', 'import sys; print(repr(sys.stdin.read()))']).stdout
        self.assertEqual(out, "''\n")

    def test_failure_does_not_expose_output_or_arguments(self):
        with self.assertRaises(runtime.CommandError) as exc:
            runtime.run([sys.executable, '-c', 'import sys; print("secret",file=sys.stderr); sys.exit(3)'])
        self.assertNotIn('secret', str(exc.exception))

    def test_rofi_cancel(self):
        self.assertIsNone(runtime.choose(['row'], 'Wi-Fi', 'theme', runner=lambda *args, **kw: result('', 1)))

    def test_rofi_index_never_becomes_user_command(self):
        for selection in ('garbage', '-1', '3', SSID):
            self.assertIsNone(runtime.choose(['row'], 'Wi-Fi', 'theme', runner=lambda *args, **kw: result(selection)))

    def test_plain_labels_and_rofi_markup(self):
        captured = []
        def runner(argv, **kwargs):
            captured.append((argv, kwargs))
            return result('0')
        self.assertEqual(runtime.choose(['evil\nrow\0icon\x1b'], 'Wi-Fi', 'theme', '<test>', runner), 0)
        argv, kwargs = captured[0]
        self.assertNotIn('\0', kwargs['input_text'])
        self.assertEqual(kwargs['input_text'].count('\n'), 1)
        self.assertEqual(argv[-1], '&lt;test&gt;')

    def test_single_menu_lock(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': temp}):
            with runtime.menu_lock('test') as first:
                with runtime.menu_lock('test') as second:
                    self.assertTrue(first)
                    self.assertFalse(second)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.status-launcher-', dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.venv = self.home / '.local/share/venvs/bumblebee-status'
        (self.venv / 'bin').mkdir(parents=True)
        themes = self.venv / 'share/bumblebee-status/themes'
        (themes / 'icons').mkdir(parents=True)
        (themes / 'default.json').write_text('{}')
        (themes / 'icons/ascii.json').write_text('{}')
        (self.home / '.config').mkdir()
        (self.home / '.config/bumblebee-status').symlink_to(ROOT / '.config/bumblebee-status')
        (self.home / '.config/rofi').symlink_to(ROOT / '.config/rofi')
        (self.home / '.local/lib').symlink_to(ROOT / '.local/lib')
        (self.home / '.local/bin').symlink_to(ROOT / '.local/bin')
        for name, source in {
            'python': '#!/bin/sh\nexit 0\n',
            'bumblebee-status': '#!/usr/bin/python3\nimport json,os,sys\nprint(json.dumps({"stdin":sys.stdin.read(),"xdg":os.environ["XDG_DATA_DIRS"],"pid":os.getpid(),"args":sys.argv[1:]}))\n',
        }.items():
            path = self.venv / 'bin' / name
            path.write_text(source);path.chmod(0o755)
        self.env = os.environ.copy()
        self.env['HOME'] = str(self.home)
        self.env.pop('XDG_DATA_DIRS', None)

    def launch(self):
        process = subprocess.Popen(['/usr/bin/bash', str(ROOT / '.local/bin/mountain-mist-status')],
                                   env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = process.communicate('sentinel stdin', timeout=5)
        return process, out, err

    def test_fallback_stdin_and_exec_pid(self):
        process, out, err = self.launch()
        data = json.loads(out)
        self.assertEqual(process.returncode, 0, err)
        self.assertEqual(data['stdin'], 'sentinel stdin')
        self.assertEqual(data['pid'], process.pid)
        self.assertEqual(data['xdg'], str(self.venv / 'share') + ':/usr/local/share:/usr/share')
        self.assertEqual(data['args'][0], '-c')
        self.assertIn('-t', data['args'])

    def test_preserve_existing_xdg(self):
        self.env['XDG_DATA_DIRS'] = '/path with spaces:/another'
        process, out, err = self.launch()
        data = json.loads(out)
        self.assertEqual(data['xdg'], str(self.venv / 'share') + ':/path with spaces:/another')

    def test_missing_installation_diagnostic(self):
        (self.venv / 'bin/bumblebee-status').unlink()
        process, out, err = self.launch()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(out, '')
        self.assertIn('missing Bumblebee venv executables', err)

    def test_incomplete_theme_diagnostic(self):
        (self.venv / 'share/bumblebee-status/themes/default.json').unlink()
        process, out, err = self.launch()
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('incomplete installation', err)

    def test_wrong_version_diagnostic(self):
        (self.venv / 'bin/python').write_text('#!/bin/sh\nexit 1\n')
        process, out, err = self.launch()
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('expected exactly bumblebee-status 2.3.0', err)


if __name__ == '__main__':
    unittest.main()
