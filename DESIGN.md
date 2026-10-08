# anu-i3wm-dotfiles — Mountain Mist v2 design (historical)

> Historical baseline design. V2 is now deployed and accepted. Some details
> below describe earlier stages (flat bar, combined audio control and staged-only
> status); [README.md](README.md) and [INSTALL.md](INSTALL.md) describe the current
> Powerline implementation and installation.

This baseline preserves the existing quiet mountain-inspired desktop: dark blue
charcoal surfaces, mist-grey text, blue and teal accents, and muted warning colours.
All changes are staged in this repository. Nothing has been deployed or activated.

## Palette

| Role | Colour | Use |
| --- | --- | --- |
| Background | `#11191c` | Desktop UI base, inactive title surfaces, selection text |
| Foreground | `#c8d1d5` | Regular text and lock clock |
| Bright foreground | `#e0e6e7` | Focused titles and urgent text |
| Blue accent | `#657f91` | Focused borders, launcher accents, idle lock ring |
| Teal accent | `#6f9291` | Focus indicator, notification frame, verification ring |
| Muted slate | `#46565b` | Inactive borders, dividers, backspace highlight |
| Muted red | `#9b6b6b` | Urgent borders and incorrect-password ring |
| Bright red | `#b77d7d` | Critical notification frame and urgent indicator |
| Yellow | `#a39a76` | Binding-mode indication |
| Selection teal | `#8aa3a5` | Selected entries in both Rofi menus |
| Raised surface | `#182326` | Launcher input and focused title background |
| Notification surface | `#182124` | Notifications and inactive focused titles |
| Warning surface | `#24191b` | Critical notifications and urgent titles |

Dunst's existing low-urgency foreground `#aab7bb` remains a secondary muted text
colour. Its power-menu counterpart's unused background token now uses `#182326`.

## Borders, spacing, and effects

i3 uses 1 px pixel borders for new tiling and floating windows. Ordinary windows
have no title strip; tabbed and stacked title text retains the palette above.
Every client colour class, including placeholders and the client background, is
explicit. No gaps are added and layouts and bindings are retained. Existing
windows will need later runtime inspection because default border settings apply
to new windows.

Rofi keeps both menus' existing sizes, padding, list structure, and corner choices.
Both use selection teal with background-coloured text. Launcher icons stay enabled;
the power menu stays text-only. There is no structural redesign in this phase.

Picom retains XRender, shadow radius 12, shadow opacity 0.35, offsets -6/-6,
inactive opacity 0.96, active opacity 1.0, and disabled fading. No compositor blur,
animations, experimental backend, or additional effects are introduced. The
existing lock-screen blur of 10 is retained independently of Picom.

## Typography

- i3 titles/bar: Noto Sans Mono 9.
- Application launcher, power menu, and Dunst: Noto Sans Mono 10.
- Lock time/date: existing DejaVu Sans, sizes 48/16.
- Kitty: unchanged; its typography is outside this baseline change.

The staged status bar is text-only and retains Noto Sans Mono; no icon font is
required. No fonts or production packages are installed here.

## Locking and startup ownership

`.config/i3/lock.sh` is the common locking entry point for xss-lock and the power
menu. The binary remains `$HOME/Downloads/i3lock-color/build/i3lock`. The script
replaces itself with that binary using `exec` and passes `--nofork`, preventing
the main locker from daemonizing away from xss-lock supervision. This does not
disable the build's internal window-raising helper process.

The existing `xss-lock --transfer-sleep-lock` startup stays in place. The wrapper
does not unset `XSS_SLEEP_LOCK_FD`, close the inherited descriptor, or background
the locker. Local build source closes the descriptor in its map-notify handler;
its internal helper also closes its inherited copy. This lets the locker signal
readiness to logind while remaining supervised until unlock.

Time is explicitly `%H:%M`; date is explicitly `%A, %d %B`, yielding, for example:

```text
23:03
Wednesday, 07 October
```

The script sets `LC_TIME=C` for English names and unsets inherited `LC_ALL` so it
cannot override that setting. Other locale environment variables are retained.
This particular build still applies the selected locale globally internally,
rather than configuring LC_TIME separately; its compose handling therefore also
uses C. Local time and timezone are retained.
Non-ASCII password composition needs explicit validation before deployment.

The indicator uses `x+w/2:y+h/2`; time uses `x+w/2:y+h/2-150`; the date uses
`tx:ty+30`; the existing invisible greeter also includes the monitor origin.
These are expressions supported by this local build. No screen selector is set,
so the clock and indicator appear on every detected monitor. Physical multi-monitor
placement, small screens, scaling, and wallpaper coverage await runtime validation.

Picom has one intended startup owner: plain i3 `exec --no-startup-id picom --config
~/.config/picom/picom.conf`. It starts at a future session startup, not every
reload or in-place restart. The existing `Hidden=true` XDG entry is retained and
documented so dex does not provide another startup path for that desktop entry.
Any external startup mechanism outside this staged snapshot must be audited at
deployment. Picom has not been started by this work.

## Staged status system

The backend produces `VOL 42% | WiFi Home 82% | BAT 92% | Wed 07 Oct | 23:03`.
It leaves workspaces on i3bar's normal left side and has not replaced i3status.
The pinned production venv will be `~/.local/share/venvs/bumblebee-status`.
`~/.local/bin/mountain-mist-status` checks the 2.3.0 pin and installation files,
prepends the venv/share root to XDG_DATA_DIRS without dropping existing roots,
then execs the foreground backend with inherited stdin/protocol stdout. Empty or
unset XDG data roots use `/usr/local/share:/usr/share`. Import-time theme discovery
still needs the bundled data even with an explicitly addressed custom theme.
The real 2.3.0 INI is `~/.config/bumblebee-status/config`; the custom theme is
`~/.config/bumblebee-status/themes/mountain-mist.json`. No i3 config changed in
Phase 3; the future line is `status_command ~/.local/bin/mountain-mist-status`.

mm_audio and mm_wifi live under `~/.config/bumblebee-status/modules`; shared
stdlib-only support lives under `~/.local/lib/mountain_mist`. mm_audio replaces
the built-in pipewire module because its subprocess timeout can fall through to
an indefinite wait. Our wpctl calls are bounded to 2 s with bounded process-group
cleanup, poll every 5 s, and always use @DEFAULT_AUDIO_SINK@. Left click mutes;
wheel changes 2% with a 1.0 ceiling. Normal is VOL percentage, muted is MUTED in
neutral blue-grey, unavailable is VOL ?. No pactl, pamixer or pulsectl is used.

mm_wifi polls cached NetworkManager data every 15 s, discovers the interface,
distinguishes radio off/down/connecting/connected/unavailable, and limits the
SSID to 20 display characters. Connected means association, not Internet access.
There are no connectivity probes or routine scans. Expected command/parse failures
are recoverable on the next refresh. Both custom modules cache text/state and
update in background workers. The engine tick is 5 s to reduce 2.3.0 theme/state
rendering overhead; background results can wait for that next draw.

Built-in battery uses a 60 s interval, 20% warning/10% critical, no remaining-time
estimate. BAT0 was confirmed read-only; the launcher falls back to auto-detection
if BAT0 is absent at startup. Charging appends `+`, full appends `full`, and both
use teal; discharging is foreground, low yellow, critical red. Two datetime aliases
give `%a %d %b` and `%H:%M`, C.UTF-8/local timezone, with 30 s/15 s refreshes. Their
click actions launch the Rofi calendar with separate input/output. The theme uses
flat #11191c, #c8d1d5 text, modest spaces and text `|` prefixes, no leading pipe,
Powerline, premade theme inheritance, emoji, or Font Awesome. Intentional Wi-Fi
off and muted audio are neutral; connected Wi-Fi is teal.

`~/.local/bin/rofi-network` uses `~/.config/rofi/network.rasi`, showing cached APs,
signal/security, saved profiles and radio/refresh/disconnect/settings actions.
Indexed menu choices are separate from raw SSID data; nmcli escapes are decoded,
and subprocesses use argument arrays. Saved networks activate by UUID (and BSSID
for a selected AP). New networks delegate to the installed nm-connection-editor,
without an SSID prefill or custom credential entry. NetworkManager/editor own
credential handling/storage. Missing existing secrets/agent, vanished APs and
PolicyKit refusal show failure/settings feedback. No passwords in argv, secret
files, secret reads or permission changes. Hidden/new network configuration is
completed in the editor, including open networks. Multiple adapters currently
prefer the first connected one; there is no adapter-picker.

`~/.local/bin/rofi-calendar` uses stdlib calendar/datetime and
`~/.config/rofi/calendar.rasi`, importing the network theme for consistent styling.
Monday-first grid, [DD] for today, previous/next month, Today and Escape/Close;
no external calendar service or Tk. Helpers use single-menu locks under the user
runtime directory (cache fallback), separate stdin, bounded process groups and
finite UI/operation lifetimes. The status launcher never redirects stdin; i3bar
must keep its click_events stream open to avoid the upstream EOF redraw defect.

Runtime dependencies: Python 3.12, Bumblebee 2.3.0, wpctl/WirePlumber/PipeWire,
nmcli/NetworkManager, Rofi, nm-connection-editor for new networks/settings, an
available C.UTF-8 locale and Noto Sans Mono. No additional Python packages.
The [compatibility report](docs/bumblebee-status-2.3.0-compatibility.md) remains
historical framework evidence; [the plan](IMPLEMENTATION_PLAN.md) records the
final mitigations, test commands, measured resources and remaining acceptance work.

48 stdlib unit tests and full pinned-engine fake-command integration passed,
including deadlines, safe events, recovery, open stdin, module/theme discovery
and repeated refreshes. Battery-state palette fixtures pass. Read-only real wpctl
and cached NetworkManager reads succeeded. Controls, authentication, GUI rendering,
Rofi interaction, hotplug, i3bar lifecycle and a live resource benchmark remain
unverified. No production venv or helper/module/theme files have been deployed;
the isolated validation venv is removed at phase completion.

## Changed files

| File | Reason |
| --- | --- |
| `.config/i3/config` | Explicit palette for clients, 1 px defaults, sole intended Picom startup |
| `.config/i3/lock.sh` | Explicit date/time, English names, direct supervision, monitor-aware positioning |
| `.local/bin/powermenu` | Lock action executes the common lock script |
| `.config/autostart/picom.desktop` | Document why its existing disabled override must remain |
| `.config/dunst/dunstrc` | Explicit Noto Sans Mono 10 |
| `.config/rofi/config.rasi` | Selection teal for application entries |
| `.config/rofi/powermenu.rasi` | Matching font and selection colours; supporting background token |
| `.local/bin/mountain-mist-status` | Pinned foreground launcher preserving i3bar input/output |
| `.config/bumblebee-status/config` | Verified INI module order, intervals, battery and calendar actions |
| `.config/bumblebee-status/modules/mm_audio.py` | Bounded default-sink audio status and controls |
| `.config/bumblebee-status/modules/mm_wifi.py` | Cached NetworkManager state and isolated helper launch |
| `.config/bumblebee-status/themes/mountain-mist.json` | Flat text-only palette and restrained separators |
| `.local/lib/mountain_mist/` | Shared stdlib subprocess, parsing, menu and calendar logic |
| `.local/bin/rofi-network`, `.config/rofi/network.rasi` | Safe indexed Wi-Fi menu and editor delegation |
| `.local/bin/rofi-calendar`, `.config/rofi/calendar.rasi` | Monday-first month navigation with existing palette |
| `tests/test_status.py`, `tests/integration_status.py` | Unit fixtures and actual pinned-engine isolated checks |
| `docs/bumblebee-status-2.3.0-compatibility.md` | Preserved framework evidence and reconciled requirements |
| `DESIGN.md` | Visual system, implementation rationale, assumptions, and file inventory |
| `IMPLEMENTATION_PLAN.md` | Later phases, acceptance checks, deployment and rollback |

Picom's actual configuration, i3status, wallpaper references, and Kitty are
unchanged. Runtime paths intentionally target the eventual home-directory
locations. Use the disposable-HOME integration harness for status previews;
do not launch staged desktop control scripts against the live HOME as validation.
