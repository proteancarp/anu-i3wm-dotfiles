# anu-i3wm-dotfiles

**Mountain Mist v2** is the visual theme of this repository: a quiet Linux Mint/X11
i3 desktop with charcoal surfaces, mist-grey text,
blue/teal accents, and a connected Powerline status bar. The deployed v2 has
been functionally and visually accepted by its owner. This README describes
the current implementation; [INSTALL.md](INSTALL.md) covers recreation and
rollback. Earlier design and compatibility documents record the work leading
to this version, rather than the current installation state.

Original work is licensed under [MIT](LICENSE); inherited i3 configuration
portions retain the [BSD notices](THIRD_PARTY_NOTICES.md). The sanitized current
tree is ready for a fresh public root commit, as recorded in
[the public-release audit](docs/public-release-audit.md). Existing private Git
history has not been sanitized and must not accompany that fresh publication.
No wallpaper redistribution permission is implied; the wallpaper is not bundled.

```text
workspaces …                         VOL 80%  MUTE  WiFi Home 57%  BAT 74%  Thu 08 Oct  13:40
```

## Desktop architecture

i3 owns tiling, ten workspaces, keybindings, startup, and i3bar. New tiling and
floating windows have 1 px pixel borders; there are no added gaps. Mod is Super
(Mod4). Window-title text uses `Noto Sans Mono 9`; the bar alone uses
`pango:Noto Sans Mono, PowerlineSymbols 9`.

The existing bar block runs `~/.local/bin/mountain-mist-status` and sets
`tray_output none`. This hides legacy tray icons without stopping NetworkManager,
Bluetooth, input indicators, or their applications. Workspaces remain on the
left; the status widgets are on the right.

| Shortcut | Action |
| --- | --- |
| Super+Return | Kitty |
| Super+d | Rofi application launcher (`drun`) |
| Super+F2 | Nemo |
| Super+Shift+s | Interactive GNOME screenshot |
| Super+Shift+f | Cinnamon settings |
| Super+Shift+p | Rofi power menu |
| Super+Shift+c / Super+Shift+r | i3 reload / restart |

The config also retains standard i3 window/layout/workspace bindings. Its plain
`exec` startup entries launch dex's XDG autostart, Picom, xss-lock, Dunst, and
feh. These entries run at initial session startup, rather than on each reload
or in-place restart. The user Picom desktop entry is `Hidden=true` so dex does
not launch a duplicate from that entry. Other host autostart entries are outside
this repository.

## Bumblebee-status and Powerline

The permanent venv is `~/.local/share/venvs/bumblebee-status`, pinned to
**bumblebee-status 2.3.0**. No installed engine source is patched. The Bash
launcher verifies that version and required files, adds the venv's `share`
directory to `XDG_DATA_DIRS`, selects the user config directory, then `exec`s
the backend in the foreground. i3bar owns its stdin and protocol stdout.

Configuration uses five modules:

```text
mm_audio, mm_wifi, battery, datetime:date, datetime:clock
```

`mm_audio` supplies two independent widgets, making the final visible order
**volume | mute | Wi-Fi | battery | date | time**. Custom modules import shared
Python helpers from `~/.local/lib/mountain_mist/`. Updates read cached snapshots
while bounded audio/network subprocesses run in background module updates.
The engine refresh interval is 5 seconds; audio polls every 5 seconds, Wi-Fi
every 15, battery every 60, date every 30, and clock every 15.

The active user theme is
`~/.config/bumblebee-status/themes/mountain-mist-powerline.json`. Both the INI
and the launcher's explicit `-t` select it; changing the INI alone cannot
override the launcher. The original `mountain-mist.json` remains a flat fallback.

The Powerline renderer inserts ** U+E0B2** before each widget: its foreground
is the current segment background and its background is the previous segment
background. Native i3bar separators and separator spacing are disabled. This
produces continuous left-pointing joins and leaves the clock as the rightmost
endpoint. Date and clock use related dark backgrounds. See
[the theme study](docs/mountain-mist-powerline.md) for bundled-theme comparisons
and exact semantic colors.

**fonts-powerline is required**, with Fontconfig family `PowerlineSymbols`.
Plain Noto Sans Mono can fall back to OpenSymbol at this private-use code point
and display the wrong symbol even after the package is installed. The explicit
bar font stack is therefore intentional. Font Awesome, a full Nerd Font, and
patched Noto are unnecessary: labels stay textual.

## Volume, mute, and battery

One audio module performs one `wpctl get-volume @DEFAULT_AUDIO_SINK@` query per
refresh, sharing an atomic percentage/mute snapshot between both widgets.
Queries and control commands have 2-second timeouts and recover from failure.

| Widget | Left click | Wheel up/down | Display |
| --- | --- | --- | --- |
| Volume | No action | ±2%, `wpctl --limit 1.0` (100% ceiling) | `VOL 80%`, including while muted |
| Mute | Toggle default-sink mute | No action, including no workspace-wheel fallback | `MUTE` / `MUTED` |

Intentional mute uses neutral slate rather than error red. Failures degrade to
`VOL ?` / `MUTE ?` and recover on later successful reads. Existing externally
amplified volume is reported accurately; the wheel controls enforce the ceiling.

The retained **keyboard media-key bindings are separate**: they use `pactl`,
±10% steps, and the old `killall -SIGUSR1 i3status` refresh. They have not been
harmonized with the new bar. The custom bar needs no pactl/pamixer/pulsectl;
the keyboard bindings need PulseAudio compatibility and do not enforce the
bar's 100% ceiling. Bumblebee observes those changes on its next audio poll.

The built-in battery module reads sysfs. The launcher chooses BAT0 when present
and otherwise requests automatic detection. Time estimates are disabled;
the optional Python `power` package is unnecessary.

| Discharging capacity | State / output | Entire segment background | Foreground |
| --- | --- | --- | --- |
| 21–100% | Normal, `BAT 74%` | Dark teal `#182326` | `#8aa3a5` |
| 11–20% | Warning, `BAT 18% LOW` | Yellow `#a39a76` | `#11191c` |
| 0–10% | Critical, `BAT 8% CRIT` | Red `#b77d7d` | `#11191c` |

Bumblebee 2.3.0 compares strictly with `<`, so the config uses
`battery.warning=21` and `battery.critical=11`. LOW/CRIT are supported native
theme suffixes. Charging/full/AC states retain teal `#6f9291` with dark text;
the built-in low-charge states apply while **discharging**.

## Wi-Fi and calendar

Click Wi-Fi to open `rofi-network`. The bar and menu read NetworkManager through
`nmcli`, decode escaped fields, and use cached access-point data with
`--rescan no`. Association/signal do not imply Internet reachability. Bar SSIDs
are sanitized and shortened to 20 characters; the menu retains search/filtering.

The menu offers cached networks, saved profiles, Disconnect, Refresh networks,
Enable/Disable Wi-Fi, Connection settings, then **Close**. Only explicit refresh
requests a scan. Saved connections activate by UUID, with interface/BSSID where
applicable. New networks and missing secrets are delegated to
`nm-connection-editor` and the host's secret-agent/PolicyKit flow; helpers do
not handle passwords. Close and Escape return success with no nmcli action.
There is no adapter chooser for multiple Wi-Fi interfaces.

Click date or time to open `rofi-calendar`. This Python-standard-library helper
shows a Monday-first current month, brackets today's date, and provides
Previous month, Next month, Today, and Close. Escape cancels. Its Rofi mainbox
contains only `message` and `listview`, so there is no search/input bar. This is
a month viewer, not an event calendar, and needs neither Tk nor a calendar service.
Date/time are local time with English `C.UTF-8` formatting.

Helper themes deliberately set child text backgrounds to transparent/inherited
colors, including selected-row text. This avoids Rofi 1.7.5's default light
rectangles. Network width is 680 px; calendar width is 430 px. Each helper has
a single-instance lock and bounded subprocess/process-group cleanup, using the
session runtime directory or a cache fallback.

## Locking, sleep, and power menu

Both xss-lock and the power menu use `~/.config/i3/lock.sh`. Its current external
dependencies are **`~/Downloads/i3lock-color/build/i3lock`** and
**`~/Pictures/wallpapers/mountain.png`**. Neither is included in this repository.
The audited build identifies as `2.13.c.5-7-ge6c0caf (2025-12-11)`; stock i3lock
does not support the script's color/blur options.

The wrapper uses `exec` and `--nofork`. With
`xss-lock --transfer-sleep-lock`, the inherited `XSS_SLEEP_LOCK_FD` stays intact
until i3lock-color closes it when the lock window maps, allowing logind's sleep
transition to continue. xss-lock also handles the X screensaver lock path.
The script supplies centered monitor-relative ring/time/date positions, blur
10, an English clock/date, teal verification and muted-red failure rings.
Verification/error text is intentionally fully transparent in the current
config; the ring carries that feedback.

Idle/DPMS timers and suspend policy come from the host, not this repository.
The power menu has Lock, Logout, Restart i3, Reboot and Shutdown, with
confirmation for the last four. **It has no Suspend item.** Suspend locking
depends on the running xss-lock/logind integration; installation must verify
actual authentication and sleep/wake ordering before relying on it.

## Picom, notifications, launcher, and terminal

Picom starts explicitly from i3 using XRender, shadows (radius 12, opacity 0.35,
offsets −6/−6), inactive opacity 0.96, active opacity 1.0, and no fading or
compositor blur. Lock-screen blur is independent. Avoid competing Picom startup
entries on a new host.

Dunst starts with the supplied config: top-right notifications, Noto Sans Mono
10, 360 px width, rounded corners, transparency 8, quiet duplicate handling,
and palette-matched urgency frames. Low/normal timeouts are 4/6 seconds;
critical notifications persist until dismissed.

Rofi's application launcher uses the same palette and normal installed icon
themes; the helpers and text-only power menu have their own themes. Selection
is `#8aa3a5` with dark `#11191c` text. Kitty uses Noto Sans Mono 11.5, 12 px
padding, a steady block cursor, matching ANSI colors, background opacity 0.92,
and a Powerline tab bar when multiple tabs exist.

## Production paths and recovery

Repository paths mirror their destinations under `$HOME`:

| Repository path | Purpose |
| --- | --- |
| `.config/i3/{config,lock.sh}` | WM, bar, startup, common locker |
| `.config/bumblebee-status/config` | Module order, intervals, parameters |
| `.config/bumblebee-status/modules/{mm_audio,mm_wifi}.py` | Custom modules |
| `.config/bumblebee-status/themes/{mountain-mist,mountain-mist-powerline}.json` | Flat fallback and active theme |
| `.config/rofi/{config,network,calendar,powermenu}.rasi` | Rofi configuration/themes |
| `.config/{picom/picom.conf,autostart/picom.desktop}` | Compositor config/startup ownership |
| `.config/{dunst/dunstrc,kitty/kitty.conf,i3status/config}` | Notifications, terminal, legacy status fallback |
| `.local/bin/{mountain-mist-status,rofi-network,rofi-calendar,powermenu}` | Executable entry points |
| `.local/lib/mountain_mist/{__init__,runtime,network,calendar_view}.py` | Shared runtime/helpers |

Only these 24 production files belong in the live tree. Tests, documentation,
`scripts/preview-powerline-status`, and temporary environments stay in the repo
or temporary storage. The permanent venv is created separately.

Backups live under `~/.local/state/mountain-mist/backups/<timestamp>/` and retain
home-relative paths. Each manifest records original/backup paths, prior
existence, checksum and mode. Newly created files must be removed on rollback,
not restored from nonexistent backups. Supplemental backups preserve the
original Phase 4A history; reversing several updates requires restoring them
newest first. [INSTALL.md](INSTALL.md#rollback) explains restoration and the
two selections required for the flat-theme fallback.

## Audit and validation

Final audit on 2026-10-08: **all 24 production files match deployed contents
and modes**. Executable launchers/helpers and lock.sh are executable. No live
files, running services, or production behavior changed during this audit.
All **53 unit tests**, **20 Powerline state/boundary frames**, the staged preview,
and the production-engine integration test passed. Installation/rollback examples
were also exercised in an isolated temporary home, including prior-file mode
restoration and removal of files that were originally absent. The venv's
`pip check` found no broken requirements.

```sh
python3 -B -m unittest discover -s tests -v
~/.local/share/venvs/bumblebee-status/bin/python -B tests/validate_powerline.py
python3 -B tests/integration_status.py ~/.local/share/venvs/bumblebee-status
git diff --check
```

The unit suite covers audio interactions/shared state, bounded failures,
Wi-Fi actions/cancellation, calendar navigation/layout, runtime cleanup and
launcher setup. Real 2.3.0 renderer fixtures cover state colors, continuous
joins, six widgets, native battery suffixes and exact 21/20/11/10/5 boundaries.
Integration runs the production launcher/engine with fake command tools, open
stdin, real click routing, refreshes, recovery and termination. It does not
exercise real audio/network controls. In this sandbox the command-socket
thread is skipped by a temporary test-only shim because Unix socket bind is
denied; stdin click tests remain active. The preview separately suppresses
controls and the command socket by design.

Static checks include i3 syntax, all four Rofi themes with staged import roots,
Bash syntax, Python AST, JSON/INI, desktop-entry validation, native Picom
libconfig and Kitty parsing, and Pango's actual separator-font selection.
Dunst has INI validation here; full native initialization requires the real
X session. The GUI/bar/Rofi appearance was accepted manually by the owner.

Remaining limitations: external locker/wallpaper provisioning and PAM policy,
legacy media-key refresh/steps, host-specific startup/secret agents, battery
hot removal/multi-adapter behavior, and suspend/authentication/multi-monitor
checks on a new machine. Helpers treat a nonzero Rofi exit as cancellation, so
some launch/render failures can look like a normal close. Upstream 2.3.0 has an
EOF redraw loop: keep backend
stdin open. Some optional-module discovery warnings are expected; the current
five modules do not require those optional dependencies. Mock performance
measurements do not establish real-session resource usage or security behavior.
