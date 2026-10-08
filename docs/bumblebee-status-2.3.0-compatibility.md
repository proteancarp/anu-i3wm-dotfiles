# anu-i3wm-dotfiles — Bumblebee-status 2.3.0 compatibility lab

> Historical isolated compatibility lab, not the current deployment guide.
> Later custom audio/Wi-Fi modules and calendar helpers supersede proposed
> integrations here. See [README.md](../README.md) for the accepted implementation.

Run 2026-10-08. Repository: anu-i3wm-dotfiles; visual theme: Mountain Mist v2.

## Scope and isolation

The earlier detailed prompt was unavailable during the lab. The lab covered the then-current request and IMPLEMENTATION_PLAN.md section 1. The restored requirements are reconciled below without treating later source inspection as a lab test. This is conditional compatibility evidence, not desktop deployment acceptance.

Effective sandbox: workspace-write, network enabled, approval policy never. Before venv creation or installation, socket.getaddrinfo resolved pypi.org and urllib.request received HTTPS HTTP 200 from https://pypi.org/simple/bumblebee-status/ (read 256 sample bytes).

Python 3.12.3. Installed exactly bumblebee-status==2.3.0 in a disposable /tmp venv. pip list showed only bumblebee-status 2.3.0 and bundled pip 24.0; pip check passed. No optional extras were installed. Package metadata has no Requires-Python field and no unconditional runtime dependency. The launcher checks Python major version, despite its error message saying at least 3.4.

Tests used disposable HOME and XDG config/data/runtime directories, an explicit empty config, no display/session bus variables, and a mock-only command PATH. NIC, CPU, PulseAudio and command actions used fixtures/mocks; battery and memory reads were read-only. No actual audio/network configuration, GUI, i3, service or desktop action was invoked. Lab child process groups were terminated and their command sockets removed.

## Findings

Python 3.12 source compilation, the tested module/custom-module APIs, i3bar output, click routing and palette rendering work subject to these limitations:

- Bare venv launcher fails before --help: RuntimeError: unable to find theme default. Themes are installed under venv/share/bumblebee-status/themes, but default search paths omit that venv location. Setting XDG_DATA_DIRS to venv/share through the supported search mechanism allows the unmodified package to run. No package source patch was made.
- nic/network require netifaces, cpu requires psutil, and pulseout requires pulsectl. None is included by the exact base install. Missing imports become error modules. memory reads /proc/meminfo despite its metadata psutil extra. battery works without power but loses time estimates.
- All 157 Python sources compile. Warnings cover invalid regex escapes in pipewire and literal identity comparisons in power_profile/power-profile. Compilation does not establish runtime support for every module.
- datetime formatting, alias parameters, leap-day and year-boundary fixtures pass on 3.12. It calls deprecated locale.getdefaultlocale and changes process-global LC_ALL. An available locale was specified. Custom user modules load on 3.12 through deprecated SourceFileLoader.load_module. Import order matters: directly importing core.output before core.config raises AttributeError; the shipped launcher uses the working order.
- Battery auto-detection without a device hides the module. An explicitly named missing battery displays 100%/AC. Mock low-charge discharging battery gets critical state.
- nic fixtures cover connected signal/SSID, disconnected critical state and disappearing interfaces. Poll interval is five seconds. The separately inspected network module attempts external TCP to 1.1.1.1:53 with no timeout; that connection path was not executed.
- pipewire reads and mute/scroll pass under mocks; volume commands use wpctl --limit 1.0 and the default sink token. Missing sink yields N/A. pasink uses pactl and retains stale volume when output contains no matching sink. pulseout fixtures verify upper clamp/mute/no device; no device yields 0% and may retain muted state. Real servers were never contacted.
- calendar's click path requires tkinter and tkcalendar. Mocking browser lookup and invoking the actual callback confirms missing tkinter here; no popup was launched. Default datetime click dispatches the external calendar command; a configured left-click overrides it.
- Input routing tries instance then name, and both callbacks execute when both are registered. Global fallback executes only if neither handles the event. Buttons 1/2/3/4/5 map to left/middle/right/up/down. Aliases supply name and widgets supply instance. Command callbacks interpolate name/instance and use shell=True. Real captured i3bar click input invoked only the lab recording stub with exact name/instance. Malformed JSON was tolerated and still caused forced update/redraw.
- Output header is version 1 with click_events true; frames are arrays containing full_text/name/instance. Normal fg/bg #c8d1d5/#11191c, warning #a39a76, and critical #b77d7d/#24191b were verified. Stream is open during execution; terminated captures were checked frame by frame.
- Update exceptions become persistent error widgets, replace the module update method and set a one-second interval. No automatic recovery occurs. Constructor/full_text/state exceptions have less isolation. Foreground slow updates block; background dispatch returns quickly and skips duplicate updates while the worker lives. Intervals and forced updates pass.
- util.cli's 60-second communicate timeout is followed by unbounded communicate without killing/terminating the child. Verified with a mock, without running a stalled command.
- stdin EOF causes repeated empty reads and redraws. The two-second closed-input sample produced 281 frames and 62,907 stdout bytes, compared with eight frames over ten seconds for the essential open-input sample. This is a resource defect for closed stdin.

Optional dependency installation compatibility, real audio/network integration, live rendering and GUI calendar behavior remain untested. No current live stack was selected or activated.

## Resource measurements

RSS is a single /proc snapshot; CPU percentage refers to one core. These short samples are environment-specific. Whole-process samples include startup; the separate steady sample begins after first frame/click. Extended smoke shows a missing-cpu error rather than a working CPU module, and command dependencies are unavailable/mocked. Results do not predict live dependency overhead.

| Sample | Duration | Frames | CPU seconds | One-core CPU | RSS KiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10-second essential modules smoke and resources | 10.036 s | 8 | 1.955 | 19.55% | 15536 |
| 10-second extended modules smoke and resources | 10.008 s | 8 | 2.054 | 20.54% | 15720 |
| closed-stdin smoke and resources | 2.015 s | 281 | 0.718 | 35.92% | 15524 |
| datetime steady, stdin open | 5.0 s | — | 0.02 | 0.4% | 15608 |

## Check evidence

21 checks confirmed the behaviors above. PASS includes expected failure modes and is not a claim of deployment readiness. One initial sensor test assertion was corrected after inspecting asbool(None): the default chooses filesystem reads; missing-command behavior requires explicit use_sensors=true.

```json
[
  {
    "check": "exact package and Python",
    "result": "PASS",
    "detail": null
  },
  {
    "check": "module load and missing optional dependencies",
    "result": "PASS",
    "detail": {
      "nic": "core.module",
      "network": "core.module",
      "cpu": "core.module",
      "pulseout": "core.module",
      "battery": "modules.contrib.battery",
      "datetime": "modules.core.datetime",
      "memory": "modules.core.memory",
      "sensors": "modules.contrib.sensors",
      "pipewire": "modules.contrib.pipewire",
      "pasink": "modules.core.pasink"
    }
  },
  {
    "check": "module update failure isolation",
    "result": "PASS",
    "detail": "update failure becomes a persistent error widget; no automatic recovery"
  },
  {
    "check": "battery absent device and critical state",
    "result": "PASS",
    "detail": "auto absent: hidden; explicit absent: 100% AC; mocked low battery: critical"
  },
  {
    "check": "datetime Python 3.12 and boundary formatting",
    "result": "PASS",
    "detail": "format, alias parameters, leap day and year boundary pass; getdefaultlocale deprecated"
  },
  {
    "check": "event routing, fallbacks and command interpolation",
    "result": "PASS",
    "detail": "instance then name both fire; global only if neither handles; buttons 1/2/3/4/5; callbacks format name/instance"
  },
  {
    "check": "audio read, mute, bounded scroll and absent sink",
    "result": "PASS",
    "detail": {
      "mocked_commands": [
        "wpctl get-volume @DEFAULT_AUDIO_SINK@",
        "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle",
        "wpctl set-volume --limit 1.0 @DEFAULT_AUDIO_SINK@ 0.02+",
        "wpctl set-volume --limit 1.0 @DEFAULT_AUDIO_SINK@ 0.02-"
      ],
      "pasink_absent_sink": "retains stale 42% when pactl returns no matching sink"
    }
  },
  {
    "check": "Wi-Fi module connected/disconnected/absent",
    "result": "PASS",
    "detail": "mock netifaces/iw: connected 50%, disconnected critical, absent interface empty"
  },
  {
    "check": "slow modules and update scheduling",
    "result": "PASS",
    "detail": {
      "foreground_block_seconds": 0.15,
      "background_dispatch_seconds": 0.0009,
      "interval_and_force": "pass"
    }
  },
  {
    "check": "subprocess timeout behavior",
    "result": "PASS",
    "detail": "60-second timeout is followed by unbounded communicate; no process termination"
  },
  {
    "check": "actual engine process_event",
    "result": "PASS",
    "detail": "real engine routes parsed clicks, forces affected updates, ignores malformed JSON and redraws"
  },
  {
    "check": "10-second essential modules smoke and resources",
    "result": "PASS",
    "detail": {
      "frames": 8,
      "cpu_seconds": 1.955,
      "elapsed_seconds": 10.036,
      "one_core_cpu_percent": 19.55,
      "rss": "VmRSS:\t   15536 kB",
      "output_bytes": 3479,
      "stderr_bytes": 0,
      "module_names": [
        "battery",
        "datetime"
      ]
    }
  },
  {
    "check": "10-second extended modules smoke and resources",
    "result": "PASS",
    "detail": {
      "frames": 8,
      "cpu_seconds": 2.054,
      "elapsed_seconds": 10.008,
      "one_core_cpu_percent": 20.54,
      "rss": "VmRSS:\t   15720 kB",
      "output_bytes": 10823,
      "stderr_bytes": 150,
      "module_names": [
        "battery",
        "cpu",
        "datetime",
        "memory",
        "pipewire",
        "sensors"
      ]
    }
  },
  {
    "check": "closed-stdin smoke and resources",
    "result": "PASS",
    "detail": {
      "frames": 281,
      "cpu_seconds": 0.718,
      "elapsed_seconds": 2.015,
      "one_core_cpu_percent": 35.92,
      "rss": "VmRSS:\t   15524 kB",
      "output_bytes": 62907,
      "stderr_bytes": 0,
      "module_names": [
        "datetime"
      ]
    }
  },
  {
    "check": "RAM and absent/present temperature readings",
    "result": "PASS",
    "detail": "memory, fixture temperature and unknown absent sensor pass; missing requested sensors command becomes persistent error"
  },
  {
    "check": "mocked CPU and pulseout APIs",
    "result": "PASS",
    "detail": "CPU critical threshold; pulseout upper clamp, mute and absent device pass; absent device retains muted state"
  },
  {
    "check": "captured click stream and steady resources",
    "result": "PASS",
    "detail": {
      "real_click_stream": "module command received matching name/instance; malformed JSON tolerated",
      "steady_seconds": 5.0,
      "steady_cpu_seconds": 0.02,
      "one_core_cpu_percent": 0.4,
      "rss": "VmRSS:\t   15608 kB",
      "stderr_bytes": 0
    }
  },
  {
    "check": "custom user module Python 3.12 API",
    "result": "PASS",
    "detail": "deprecated load_module path successfully loads alias and widget"
  },
  {
    "check": "calendar missing GUI dependency",
    "result": "PASS",
    "detail": "mocked browser lookup; calendar click fails with missing tkinter; no GUI started"
  },
  {
    "check": "all source compilation",
    "result": "PASS",
    "detail": "157 Python source files compile"
  },
  {
    "check": "palette warning and critical output",
    "result": "PASS",
    "detail": "warning #a39a76; critical #b77d7d on #24191b; core.config must be imported before core.output"
  }
]
```

## Cleanup

At lab completion, the temporary environment, pip cache, fixtures, config, captures and lab process sockets had been removed. The report was the retained artifact, originally stored outside the repository. Git status and diff checks were clean at that point; no tracked file or live configuration had changed. This later documentation-only preservation intentionally creates an uncommitted documentation diff.

## Restored requirements: evidence reconciliation

"Recorded" below means the saved lab report establishes the result. "Source
verified" means read-only inspection of upstream tag v2.3.0 during documentation
normalization; it is not an additional runtime test. UNVERIFIED identifies missing
evidence. Recommendations are implementation decisions, not measured outcomes.

| Requirement | Explicit answer |
| --- | --- |
| 1. Python 3.12 verdict | Conditional compatibility on **Python 3.12.3**: 157 sources compile, tested APIs/custom module and captured streams work with theme discovery fixed. All modules, dependency installation, and live integration are **UNVERIFIED**. Deprecated APIs still work in this interpreter; no verdict for newer Python versions. |
| 2. Exact version | **bumblebee-status 2.3.0**, installed with an exact pin; no extras. Bundled pip 24.0 was the only other listed package. |
| 3. Warnings/errors | Recorded: missing default theme before argument parsing; missing netifaces/psutil/pulsectl imports; absent power/time estimates; missing tkinter/calendar callback; regex escape and literal identity syntax warnings; direct core.output import-order AttributeError; expected simulated update/command failures. Extended capture had 150 stderr bytes and a missing-cpu error. The full original stderr/transcripts were removed, so any unrecorded exact warning text is **UNVERIFIED**. Deprecated API use was inspected; a printed deprecation warning is **UNVERIFIED**. |
| 4. Actual pipewire behavior | The actual built-in module ran with mocked CLI calls: parsed `Volume: 0.42 [MUTED]` as `42%` plus muted state; buttons invoked the recorded wpctl commands with 2% steps and a 1.0 limit. Missing-command/sink failure produced `N/A`. Extended smoke loaded the module with commands unavailable. Actual server/device behavior and live default-sink changes are **UNVERIFIED**. |
| 5. Actual battery behavior | Actual module with fixtures: no auto-detected device hides the block; explicitly missing device displays `100%`/AC; mocked 5% discharging capacity gets critical state. Battery loaded in captured smoke; raw host battery readings/capacity/charging status were not retained and are **UNVERIFIED**. No power package means no time estimates. |
| 6. Actual date/time behavior | `datetime` ran with an available explicit locale, alias parameters and `%a %d %b %H:%M`; leap-day/year-boundary fixtures and captured output passed. Separate `date` and `time` modules, exact intended split layout, midnight rollover scheduling and locale fallback failures are **UNVERIFIED** at runtime. |
| 7. Actual event handlers | Actual input API and engine process_event passed synthetic clicks. Instance then name handlers can both run; global fallback only if neither handles the button. Shell command callbacks interpolate name/instance. Captured click stream invoked a harmless recording stub with matching identifiers; malformed JSON still causes update/redraw. Real i3bar/user interactions are **UNVERIFIED**. |
| 8. Exact custom-module path | Tagged source verifies `$HOME/.config/bumblebee-status/modules/mm_wifi.py` for module `mm_wifi` (name before any alias). Lab verified the same user-module directory pattern with `lab_custom.py` under disposable HOME. `mm_wifi` has not been implemented in this repository and is **UNVERIFIED**. This lookup is hard-coded under HOME; setting XDG_CONFIG_HOME alone does not redirect it. |
| 9. Exact custom-theme path | Tagged source verifies `$HOME/.config/bumblebee-status/themes/mountain-mist.json` as a supported user path for theme `mountain-mist`. Also supported: `$HOME/.local/share/bumblebee-status/themes/mountain-mist.json`. Lab palette rendering used an explicitly addressed disposable JSON theme; discovery of the intended custom-theme pathname is **UNVERIFIED** at runtime. Neither future file was created by the lab or this documentation task; live-path contents are **UNVERIFIED**. |
| 10. Smoke results | Essential battery/datetime: 8 frames in 10.036 s, 3,479 stdout bytes, no stderr. Extended battery/datetime/memory/sensors/pipewire/cpu: 8 frames in 10.008 s, 10,823 stdout bytes, 150 stderr bytes, cpu shown as missing-dependency error. Valid headers/frame JSON; no live i3 connection. Closed stdin: 281 frames/62,907 bytes in 2.015 s. |
| 11. Resource snapshot | Recorded table above: RSS 15,524–15,720 KiB. Steady datetime/open-input sample: 15,608 KiB, 0.02 CPU s over 5 s (0.4% of one core). Ten-second startup-inclusive CPU measurements were approximately 20%; they are not steady baseline overhead. Complete intended bar with real tools is **UNVERIFIED**. |
| 12. Incorrect earlier assumptions | A plain venv executable is not launch-ready; base install does not make every candidate module available; the apparent 60 s command timeout is not a bound; a closed-input smoke launch is not representative of i3bar; exceptions are not all recoverable; built-in calendar is not a Rofi calendar. These correct possible planning assumptions, rather than asserting that each was explicitly promised in DESIGN.md. Separate date/time acceptance and live PipeWire validation must not be inferred from the datetime/mocked-audio results. |
| 13. Should we use 2.3.0? | **Yes, conditionally as the pinned implementation target**, with the runtime mitigations below. Do not approve activation until real-tool availability, bounded-command behavior and complete baseline tests pass. No comparison with another release was performed. |
| 14. Recommended changes | Keep built-in pipewire only behind bounded wpctl execution and later live validation; custom stdlib/nmcli mm_wifi; auto-detected battery without estimates; two aliased datetime instances for date/time; override calendar clicks with an asynchronous Rofi helper; explicit text-only theme; safe theme search path; inherited open stdin; bounded recoverable command handling. |
| 15. Cleanup and Git | Recorded clean at lab completion, all temporary environment/cache/fixtures/captures/sockets removed. No venv recreated during documentation work. Current changes are documentation only and intentionally uncommitted; current Git is therefore not claimed clean. |

## Production implementation rules

These are requirements for later implementation, not installed launcher code or
changes to i3. Proposed installation paths must be confirmed in Phase 2.

### A. Theme discovery and XDG_DATA_DIRS

For a venv rooted at `STATUS_VENV`, prepend **`$STATUS_VENV/share`**. Bumblebee
appends `bumblebee-status/themes` itself; do not prepend the theme directory or
site-packages. This is needed before import/argument parsing even if `-t` points
to a custom theme, because import-time defaults construct the default theme.
Preserve existing XDG entries; use `/usr/local/share:/usr/share` if unset or empty.

The proposed dedicated venv is `$HOME/.local/share/mountain-mist/venv`. If selected,
the future `mountain-mist-status` launcher should follow this Bash sketch:

```bash
STATUS_VENV="$HOME/.local/share/mountain-mist/venv"
export XDG_DATA_DIRS="$STATUS_VENV/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
# Later: exec the absolute "$STATUS_VENV/bin/bumblebee-status" with reviewed args.
```

Use quoted paths, no eval, no reliance on virtualenv activation, and fail clearly
if the executable/bundled default theme is absent. Export only in the launcher
process. Do not change session-wide environment or HOME to obtain isolation in
production. The prefix has priority over inherited XDG roots, although upstream
also searches the current directory first; choose a known working directory and
pass the custom theme by absolute filename stem to avoid unrelated theme lookup.
Custom module lookup remains under real HOME until separately authorized deployment.

Lookup rules are source verified in [v2.3.0 theme.py](https://raw.githubusercontent.com/tobi-wan-kenobi/bumblebee-status/v2.3.0/bumblebee_status/core/theme.py)
and [module.py](https://raw.githubusercontent.com/tobi-wan-kenobi/bumblebee-status/v2.3.0/bumblebee_status/core/module.py).

### B. Preserve i3bar's input stream

At EOF, readline returns an empty string immediately. The engine does not break:
it passes that string into process_event, catches the JSON parse error and still
forces update/draw. Repetition explains the measured redraw storm. An empty list
of affected names can also cause all modules to update, bypassing their intervals.
This is an engine bug; changing the polling interval or input_delay is not a fix.
See [v2.3.0 engine](https://raw.githubusercontent.com/tobi-wan-kenobi/bumblebee-status/v2.3.0/bumblebee-status).

Normal i3bar operation with the program header `click_events: true` supplies a
continuing stdin click stream, kept open even between clicks. This follows the
[i3bar protocol](https://i3wm.org/docs/i3bar-protocol.html); a live session test is
still **UNVERIFIED**. `click_events` is a status-program header field, not a new
i3 config directive. Bumblebee already emits it; preserve the header unchanged.

At future deployment, launch foreground `mountain-mist-status` directly as i3bar's
`status_command`; the launcher must exec Bumblebee with inherited stdin/stdout.
Never use `/dev/null`, a closed pipe, backgrounding, daemonization or an output-only
pipeline for the bar. Development smoke harnesses must hold the stdin writer open
until terminating the child and drain stdout/stderr. Interactive helper children
must get their own stdin (usually DEVNULL), so they cannot consume bar click input.
Shutdown must terminate the bar; normal configuration does not repair unexpected
EOF if i3bar disappears without terminating it. Verify that lifecycle later.

### C. Bound every external command

`util.cli.execute(wait=True)` is not bounded: after a 60-second communicate timeout
it waits again without a timeout. `ignore_errors=True` changes error reporting,
not this behavior. `wait=False` returns promptly but does not guarantee eventual
child termination or pipe cleanup. Source: [v2.3.0 CLI API](https://raw.githubusercontent.com/tobi-wan-kenobi/bumblebee-status/v2.3.0/bumblebee_status/util/cli.py).

Inspected exposure includes pipewire/wpctl, pasink/pulseaudio/pactl,
nic/iw, sensors/sensors and any shell module or synchronous command callback that
uses this API. These are examples, not a runtime audit of every module. The network
module has a separate unbounded socket-connect path. Foreground updates block the
update lock; synchronous click actions can block input processing. A background
worker avoids blocking the main thread but does not itself bound subprocess life.

**Built-in pipewire is affected** on both reads and mute/scroll actions, as verified
in [v2.3.0 pipewire.py](https://raw.githubusercontent.com/tobi-wan-kenobi/bumblebee-status/v2.3.0/bumblebee_status/modules/contrib/pipewire.py).
Retain it only with a launcher-local `wpctl` shim before the normal PATH. The
proposed shim directory is `$HOME/.local/libexec/mountain-mist/timeout-bin`; it must
invoke the pre-resolved absolute real wpctl path, avoiding recursion. Implement
with Python stdlib, no new Python dependency: allow 2 seconds for wpctl, then
terminate its process group, allow 1 second, kill/reap if needed within another
second. Return nonzero on timeout. This bounds reads to roughly 4 seconds including
cleanup; pipewire's caught read failure becomes N/A. Verify the shim with a hung
fake binary before accepting built-in audio. Plain unwrapped wpctl is not accepted.

Catch audio click failures in bounded command helpers: override built-in
left-click/wheel-up/wheel-down with equivalent safe actions, 2% step and upper
limit 1.0, or provide equivalent callback protection in an explicitly reviewed
adapter. Built-in action exceptions can escape before forced refresh; test the
failure route, refresh after completion and allow the next click. Do not silently
patch installed Bumblebee. The shim still protects built-in status reads.

For **mm_wifi**, use stdlib subprocess with argument lists and `shell=False`,
absolute/resolved nmcli path and deterministic child locale. Use 2-second read
deadlines and a five-second poll interval. Catch TimeoutExpired, FileNotFoundError,
nonzero exit and parse/device failures inside the module and return a recoverable
`WiFi unavailable`/disconnected state; retry next poll rather than letting upstream
replace the update method permanently. Cache the result, keep full_text/state
nonblocking, and parse nmcli escaping correctly for SSIDs containing colons or
backslashes. No external Internet probe, netifaces or iw is needed.

For **Rofi helpers**, launch asynchronously, give children separate stdin, allow
only one menu per helper, and reap/clean up. Use an owned stdlib Popen lifecycle
with drained or redirected output; util.cli.execute(wait=False) alone is not a
process supervisor. Apply the same process-group cleanup
policy (1-second TERM grace, then KILL and bounded reap). Suggested hard operation
budgets: reads 2 s; scan 10 s; connect/disconnect 45 s with nmcli's own wait set
below that bound (e.g. 40 s). Report failure/cancellation without logging secrets
or turning a failed operation into a success. Treat Rofi's nonzero dismissal as
cancellation; give interactive menus a separate 300-second absolute
deadline, not a two-second query timeout. Close only that helper's descendants on
expiry. Calendar uses Python stdlib calendar/datetime and Rofi; no external
calendar service. Cap total helper execution at 600 seconds for Wi-Fi and 300
seconds for calendar, including reopened menus, rather than looping through fresh
menu deadlines indefinitely. These budgets are proposed
implementation policy, not lab measurements; later review can adjust them.

### D. Dependencies and baseline selection

Exact recorded missing/degraded candidates and their disposition:

| Candidate | Missing dependency / observed consequence | Classification for intended design |
| --- | --- | --- |
| nic, network | netifaces: module load becomes error | **NOT REQUIRED**; replace with mm_wifi/nmcli |
| cpu | psutil: module load becomes error | **OPTIONAL LATER**; no CPU block initially |
| pulseout | pulsectl: module load becomes error | **NOT REQUIRED**; use command-based pipewire |
| battery | power: remaining-time estimates unavailable, percentages still work | **OPTIONAL LATER**; explicitly disable remaining-time display |
| calendar | tkinter: click raises missing-module error | **NOT REQUIRED**; use Rofi calendar |
| calendar | tkcalendar: source requires it, but import was not reached after tkinter failure | **NOT REQUIRED**; its installed/missing state is **UNVERIFIED** |
| pasink / audio popup utilities | tkinter: popup utility import unavailable | **NOT REQUIRED**; no built-in audio popup |
| sensors with use_sensors=true | sensors executable unavailable in isolated PATH; update becomes persistent error | **OPTIONAL LATER**; actual host executable availability **UNVERIFIED** |
| pipewire | wpctl deliberately unavailable in smoke PATH; output N/A | **REQUIRED FOR OUR DESIGN**; actual host availability/server integration **UNVERIFIED** |

Memory loaded and read /proc/meminfo without psutil: metadata declaring a memory
extra is not evidence that the tested implementation needs it. No memory/thermal
block is in the initial baseline. Disabled PATH access does not prove a host tool
is absent. No dependency may be silently installed based on this table.

Baseline runtime requirements are **Python 3.12**, **bumblebee-status==2.3.0**,
**wpctl with an operational PipeWire/WirePlumber stack**, **nmcli with an operational
NetworkManager-managed Wi-Fi device**, **Rofi**, an available locale, and a text font
already selected as Noto Sans Mono. Python stdlib supplies subprocess deadlines
and calendar rendering. **No additional third-party Python packages** are required
by the proposed baseline, and no Font Awesome, netifaces, psutil, pulsectl, power,
tkinter or tkcalendar is required. Tool/server availability and versions remain
**UNVERIFIED by this report**. i3/i3bar is the eventual host, not a new installation
authorized here. A stdlib timeout shim avoids making GNU timeout another required
executable.

### Layout, remaining acceptance work and Phase 3 recommendation

Target: `VOL 42% | WiFi Home 82% | BAT 92% | Wed 07 Oct | 23:03`.

Use `pipewire`, `mm_wifi`, `battery`, `datetime:date`, `datetime:clock` in that
order. Set date format `%a %d %b` and clock format `%H:%M`, the same confirmed
English-capable locale for both, battery auto-detection and showremaining=false,
and an explicit text-only theme with labels/separators. Prefer two aliases of the
tested datetime implementation over assuming separate date/time modules were
tested. Set date refresh to at most 60 seconds so midnight rollover does not wait
for an hourly default; verify timezone, rollover and exact layout later. Poll
audio at 2 seconds and Wi-Fi/battery at 5 seconds, with a one-second engine tick;
these are proposed production settings. Override date/clock left-click with the
Rofi calendar helper, launch asynchronously, and avoid dual widget/module bindings
that would invoke two helpers for one event. Neutral/muted states should not
automatically become actionable red warnings.

**Recommend beginning Phase 3 as staged implementation once separately requested.**
The report is sufficient to design and implement mitigations with fixtures; there
is no need to recreate the venv just to preserve these findings. Implementation
acceptance still requires tool/locale/stack discovery, custom modules/helpers/shim
tests, exact full-layout captures, recoverable command failures, real PipeWire
read-only validation, and complete-bar resource measurements. Live activation is
blocked until later authorized integration checks and deployment/rollback review.
Neither starting implementation nor installing/deploying anything is authorized
by this documentation-only task.
