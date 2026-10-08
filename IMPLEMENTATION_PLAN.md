# anu-i3wm-dotfiles — Mountain Mist v2 implementation plan (historical)

> Historical Phase 3 plan and evidence. Deployment and later Powerline/audio
> refinements have since been completed and accepted. References below to future
> installation, no deployment, combined audio, or 20/10 thresholds describe that
> earlier phase. Use [README.md](README.md) and [INSTALL.md](INSTALL.md) for the
> current setup and inclusive battery boundaries.

Phase 3 now contains staged implementation and isolated validation. No live
configuration, staged i3 status_command, services or running session have changed.
The production environment has not been installed. Deployment and commits remain
outside this phase.

## 1. Bumblebee-status compatibility test

Completed on Python 3.12.3 with exactly bumblebee-status 2.3.0. The
[preserved compatibility report](docs/bumblebee-status-2.3.0-compatibility.md)
remains the historical evidence for framework behavior and the restored 15
requirements. Phase 3 implements custom bounded audio instead of the report's
proposed built-in pipewire/shim solution. No installed Bumblebee source is patched.
Keep i3status as the fallback.

## 2. Production installation and launcher

The selected future venv root is `$HOME/.local/share/venvs/bumblebee-status`.
`.local/bin/mountain-mist-status` checks executable/data/config/module/helper
availability and exactly version 2.3.0. It prepends the venv's `share` directory to
XDG_DATA_DIRS, preserving inherited roots or using `/usr/local/share:/usr/share`
when unset/empty. It selects a known working directory, passes the absolute theme
stem with `-t`, loads the real 2.3.0 INI with `-c`, and execs Bumblebee without
redirecting stdin or protocol stdout. Diagnostics go to stderr. No shell activation
is needed.

The INI has `[core]` and `[module-parameters]`, verified against 2.3.0. The program
emits `click_events: true`. At future deployment i3bar must own its open stdin:
no /dev/null, closed pipes, backgrounding, or output-only pipeline. Helper input
is separate. Unexpected EOF remains an upstream defect; check i3bar shutdown
terminates the backend during authorized integration validation.

Installation is a later authorized action. Do not install system packages or deploy
repository files implicitly. Exact future i3 line, **not applied**:

```i3
status_command ~/.local/bin/mountain-mist-status
```

Workspaces remain at the normal left of i3bar; no i3 layout/config changes were
needed for this backend work.

## 3. Status modules and theme

Staged target: `VOL 42% | WiFi Home 82% | BAT 92% | Wed 07 Oct | 23:03`.
Module order is mm_audio, mm_wifi, battery, datetime:date, datetime:clock.

- mm_audio: default-sink wpctl queries every 5 s, in a background update with
  cached text/state. Shows VOL percentage, MUTED, or VOL ?. Click commands have
  deadlines and no dependencies on pactl/pamixer/pavucontrol/pulsectl.
- mm_wifi: cached NetworkManager association state every 15 s, in a background
  update with cached text/state. Shows SSID (max 20 characters), optional signal,
  down, off, connecting or ?. This is not an Internet-reachability indicator.
- battery: builtin, 60 s, thresholds 20%/10%, no time estimates. BAT0 was confirmed
  through read-only sysfs. The INI selects BAT0; the launcher uses auto-detection
  instead if BAT0 is absent at startup, avoiding an explicitly absent device's
  misleading 100%/AC output. Discharging is plain, charging appends `+`, full
  appends `full`, and charging/full use teal. Hot disappearance is a remaining
  upstream runtime limitation.
- date/clock: two aliases of validated datetime, `%a %d %b` and `%H:%M`, using
  C.UTF-8 and the existing local timezone. Date polls every 30 s and clock every
  15 s. Both left clicks open the bounded Rofi calendar asynchronously.

Engine tick is 5 s: profiling showed the one-second rendering tick added avoidable
CPU cost in 2.3.0. Background completion updates cached output; regular drawing
may wait until the next tick. Minute rollover can be delayed up to roughly 15 s
for clock / 30 s for date plus scheduling overhead; validate that tradeoff live.

The self-contained flat Mountain Mist theme is at the actual user lookup path
`.config/bumblebee-status/themes/mountain-mist.json`; no icon set, emoji or premade
inheritance. Text pipes are block prefixes, preventing a leading separator or
Powerline decoration. Normal fg/background are #c8d1d5/#11191c, connected/charging
teal, warning battery yellow, critical red, muted/off neutral blue-grey. Custom
modules live in `.config/bumblebee-status/modules`; shared stdlib code lives in
`.local/lib/mountain_mist`. Deploy this directory layout together later.

## 4. Audio controls and process bounds

Custom mm_audio supersedes built-in pipewire and the proposed wpctl shim, so no
shim or patched package is needed. WirePlumber 0.4.17 CLI help/output and upstream
0.4.17 source confirmed the get-volume syntax and --limit semantics.
Source reference: [WirePlumber 0.4.17 wpctl](https://raw.githubusercontent.com/PipeWire/wireplumber/0.4.17/src/tools/wpctl.c). Commands
always target @DEFAULT_AUDIO_SINK@; device changes are re-read naturally. Left
click toggles mute, wheel changes by 2%, both directions have --limit 1.0. Existing
amplified readings above 100% are displayed honestly; our controls enforce 100%.

Shared runtime.run uses argument arrays, shell=False, C child locale, explicit
communicate timeouts and process groups. On timeout it sends TERM, allows 0.3 s,
then KILL with a further bounded 0.3 s cleanup. No unbounded retry/wait follows.
Audio and ordinary NM queries use 2 s command deadlines. Expected command/parse
failures stay inside custom modules and retry on refresh; they do not trigger
Bumblebee's permanent error-module replacement. Output/state callbacks do no I/O.
Audio clicks are synchronous but bounded; no real changing command was tested.

Read-only live get-volume and cached NM queries worked. Actual mute/scroll, sink
hotplug, concurrent controls, authentication and desktop rendering remain for
separately authorized integration checks.

## 5. Wi-Fi control and authentication

mm_wifi discovers adapters, checks radio, prefers a connected/connecting adapter
and reads escaped nmcli fields. All ordinary AP reads use `--rescan no`; no network
probe is performed. With multiple adapters the first connected adapter is shown;
the initial UI does not expose adapter selection.

`.local/bin/rofi-network` and `.config/rofi/network.rasi` present cached APs with
signal/security, saved profiles, disconnect, explicit refresh, radio toggle and
connection settings. Display labels are sanitized and indexed separately from
raw values. Escaped colons/backslashes survive parsing. Saved activation uses
UUID, discovered interface and AP BSSID when selected from the visible list.
A vanished AP/permission failure shows a retry/settings message and no false
success. Cancellation does no control action. Explicit refresh is the only scan.

New networks, including open/hidden/secured networks, delegate to the installed
nm-connection-editor; the helper does not prefill an SSID or implement a password
prompt. The user completes configuration in that editor. Saved profiles use
NetworkManager's normal existing secrets/secret agents; no --ask, password argument,
secret query/file or permission change. Missing secrets/agent or PolicyKit rejection
may cause activation to fail; open that UUID in the editor instead. The editor and
NetworkManager own any credential storage, not this helper. Live authentication
and editor interaction were not exercised.

Helpers get their own input, sanitized Rofi index selection, a single-menu lock,
owned subprocess lifecycle and bounded total duration. Query deadline 2 s; actions
12 s with NM wait 10 s, activation 45 s with NM wait 40 s; menus/editor up to 300 s;
Wi-Fi helper total 600 s. Output is captured/drained, command diagnostics exclude
arguments and raw output, and exceptions/cancellation clean up owned processes.
No third-party Python package is required. Installed dependencies found read-only:
wpctl/WirePlumber 0.4.17, nmcli/NetworkManager 1.46.0, Rofi 1.7.5 and
nm-connection-editor (network-manager-gnome 1.34.0+mint3).

## 6. Calendar

`.local/bin/rofi-calendar` uses stdlib calendar/datetime and
`.config/rofi/calendar.rasi`, which imports the matching network theme. It starts
at this month, Monday-first, marks today with [DD], and offers Previous month,
Next month, Today and Close. Escape cancels. Year boundaries and leap years are
covered by fixtures. Menus have separate stdin and a single-instance lock, with a
300 s total helper lifetime; no Tk/tkcalendar package or external event service.

## 7. Icon/font decision

Compare a text-first bar with a small consistent icon set. Verify glyph coverage,
baseline alignment, legibility, and actual installed font matches. Decide whether
additional fonts are necessary and obtain installation authorization if needed.
Keep Kitty typography unchanged unless separately requested.

## 8. Optional CPU/RAM/temperature modules

Add only if useful after the essential bar is stable. Use slow enough polling to
avoid needless load, discover temperature sensors rather than hard-coding them,
and handle unavailable readings gracefully. Establish meaningful thresholds and
avoid permanent warning colours for routine activity.

## 9. Final lock-screen refinement

Verify the exact executable's build provenance and supported options before any
binary relocation. Test common-script manual locking, idle locking, logind locking,
suspend/resume, inhibitor release timing, failed authentication, and supervision
until unlock. Validate English date/time, keyboard layout and compose behavior,
all monitor origins, mixed scaling, hotplug, and wallpaper coverage. Assess whether
the retained transparent verification/error text needs visible feedback. Keep a
known-working lock path available while making refinements.

## 10. Deployment

Deployment is a separate authorized phase. Capture a dated backup of every live
file to be replaced, including permissions and which files were absent. Record
the reviewed repository revision/diff and deploy only the agreed files. Audit
autostart sources beyond this snapshot so Picom and xss-lock each have one owner.
Plan explicit activation steps; an i3 reload alone will not run Picom's plain
`exec` startup line. Do not silently install dependencies or relocate the locker.

## 11. Validation and rollback

Before deployment, repeat shell, i3, Rofi, desktop-entry, and configuration checks.
After authorized activation, verify window focus/urgency colours, border widths,
both Rofi menus and confirmation dialogs, Dunst font, unchanged Kitty typography,
compositor stability, bar interaction, and locking/suspend behavior. Test on every
display configuration used in practice. Confirm resource usage remains modest.

If any acceptance check fails, restore the backed-up files and their permissions;
remove only files that were absent before deployment. Restore the original
i3status startup if the new bar fails. Revert compositor startup ownership along
with its configuration. Carry out necessary reload/session activation only with
authorization in that phase, and validate the restored baseline. Do not remove
backups until the redesigned session has been accepted.

## Phase 3 validation and readiness

48 unit tests pass: audio parsing/failures/timeout recovery/default-device refresh/
click arguments and ceiling, escaped NM rows and state transitions, menu safe UUID
activation/delegation/cancellation/failures/radio controls, calendar boundaries/
Today, real harmless subprocess deadlines and descendant cleanup, single-menu
locks, and launcher XDG/exec/stdin/install diagnostics. Unit tests need only stdlib:

```bash
python3 -B -m unittest discover -s tests -v
```

The isolated integration venv contained exactly bumblebee-status==2.3.0 and bundled
pip, with no extras. `tests/integration_status.py PATH_TO_VENV` creates a disposable
HOME under the repo, attaches actual staged modules/config/theme to the real pinned
engine, preserves open stdin and replaces all wpctl/nmcli/control/UI commands with
fakes. Captured five-block JSON, click_events, theme colors, exact module discovery,
XDG preservation, synthetic audio/network/calendar clicks, timeouts/failures and
recovery pass. Repeated normal 15 s Wi-Fi cycles pass without an EOF redraw storm.
Battery theme fixtures additionally cover discharging/charging/full/warning/critical.
Bash syntax, Python source compilation, both Rasi parses without X, INI/JSON parsing,
pip check and Git whitespace validation pass. Shellcheck is unavailable here.

Controlled full-backend snapshot over 31 s: RSS 18,892 KiB, PSS 13,554 KiB,
1.14 CPU s (3.68% of one core); 23 frames across the complete integration run
including synthetic/failure events, no stderr. These measure the backend with
Python fakes and read-only battery, not a final live benchmark; child-tool CPU is
not included. A one-second engine tick was measurably worse, motivating 5 s.
Temporary venv/fake HOME/cache/profile artifacts are removed before completion.

Recommend a separately authorized production installation and supervised live
validation next, not immediate unreviewed activation. Remaining checks: full bar
appearance/typography, actual controls and default-device changes, Wi-Fi/security/
PolicyKit/secret-agent behavior, editor delegation, GUI cancellation/navigation,
Rofi rendering, suspend/resume and i3bar process shutdown, midnight rollover and
hot battery/device disappearance, and final live resource budget. Before deployment,
review exact file list and backup/rollback paths. The current i3status startup is
unchanged; installation, deployment, reload and commit remain separate actions.

## Baseline validation scope

The original baseline phase could check Bash syntax, i3 parse validity without autostart,
Rofi Rasi validity without X, the disabled desktop entry, Dunst's INI structure,
Picom's libconfig syntax, and script dispatch using harmless mocks. It can inspect
local i3lock-color source for option support, coordinate semantics, and descriptor
handling. It cannot establish runtime rendering, PAM/authentication success,
suspend safety, real monitor placement, or compositor behavior without a later
authorized session test. No daemon is started to validate Dunst or Picom.

See [DESIGN.md](DESIGN.md) for the file-by-file baseline change inventory.

Baseline checks completed: `bash -n` for both scripts; `i3 -C -c` with display
variables unset and a repository-local temporary runtime directory; Rofi
`-rasi-validate` for both files with display variables unset;
`desktop-file-validate`; Dunst INI parsing; Picom parsing through the installed
libconfig library; and `git diff --check`. Harmless mocks confirmed both locking
entry points retain their PID through exec, pass the expected options, and inherit
the sleep descriptor. `fc-match` resolved Noto Sans Mono to NotoSansMono-Regular.ttf.
The Git diff was manually reviewed. Temporary validation files were removed.
