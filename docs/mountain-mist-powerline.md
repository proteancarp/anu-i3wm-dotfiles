# anu-i3wm-dotfiles — Mountain Mist v2 Powerline theme

The Powerline theme lives alongside the original flat fallback theme at
`.config/bumblebee-status/themes/mountain-mist-powerline.json`, the user-theme
directory verified in the installed Bumblebee-status 2.3.0 `core/theme.py`.
The production config and launcher select it. The i3 bar uses a bar-only
`font pango:Noto Sans Mono, PowerlineSymbols 9` stack; the global/window-title
font is unchanged. Refinements were backed up and deployed before activation;
the owner has since accepted the real bar and Rofi appearance. See
[README.md](../README.md) and [INSTALL.md](../INSTALL.md) for the current setup.

## Installed themes inspected

All six requested variants actually exist in the production venv's
`share/bumblebee-status/themes/` directory:

| Theme | Pattern | Borrowing decision |
|---|---|---|
| greyish-powerline | Two alternating grey backgrounds; state backgrounds replace normal backgrounds | Restrained related backgrounds, not its yellow/red palette |
| nord-powerline | Four related slate backgrounds, explicit charging/charged backgrounds | Cohesive blue/teal family and visible state changes |
| iceberg-powerline | Six-step dark-to-light ramp with foreground contrast changes | Contrast-aware foregrounds, not the very light ramp |
| iceberg-dark-powerline | Seven-step dark slate ramp with mostly stable foreground | Closely related dark date/time backgrounds |
| onedark-powerline | Two alternating dark backgrounds with state overrides | Compact design; avoid positional alternation when semantics matter |
| solarized-powerline | Two backgrounds, different foregrounds and attention-state fills | Dark text on lighter state fills |

Also inspected `powerline.json`, `powerline-pango.json`, `default.json`,
`icons/ascii.json`, `icons/awesome-fonts.json`, and the installed theme/output
renderer. These six variants obtain `separator: U+E0B2`, padding and icon prefixes
from `awesome-fonts`, rather than declaring the separator in each theme.
`powerline-pango` illustrates markup; this design uses native i3bar color fields.

### Rendering and override behavior

`core/output.py` inserts a decorator JSON block **before** each widget. Its glyph
foreground is the current widget's background; its background is the previous
widget's background. The first decorator has null/unset previous background,
falling back to i3bar's existing `#11191c`. Both the decorator and content use
`separator: false` and `separator_block_width: 0`, so no i3bar gap interrupts
the connection. Decorator/content share widget IDs, preserving click targets.

`core/theme.py` resolves defaults, positional cycle, top-level properties,
module name/alias properties, then widget state overrides. Content foregrounds
are explicit `fg` values, not automatically contrast-calculated. Decorator
foregrounds are derived from the final state-resolved `bg`. This theme uses
module-specific fills instead of a positional cycle, so each module keeps its
identity when state changes. All transition colors are checked against the
real 2.3.0 output renderer.

### Separator direction

The only selected glyph is ** U+E0B2 POWERLINE LEFT HARD TRIANGLE**. For this
renderer, its triangle belongs to the current segment and points into the
previous background to its left. That is the bundled themes' direction and
matches the right-aligned group: an angled leading edge, continuous joints,
and the clock content at the far-right endpoint with no trailing arrow.

U+E0B0 **** is the opposite, right-pointing hard triangle. U+E0B1 **** and
U+E0B3 **** are the respective thin dividers. They are different glyphs, not
automatic left/right separator settings. Swapping E0B2 for E0B0 without changing
the renderer's foreground/background geometry would reverse the intended join.

## Font audit

**PowerlineSymbols is now installed manually.** `fc-match 'Noto Sans Mono'` selects Noto
Sans Mono, but it does not cover E0B0–E0B3. Before installation,
`fc-list ':charset=e0b2'` found only LibreOffice OpenSymbol; the other three code
points also found only OpenSymbol. Plain Noto's fallback still selects OpenSymbol
after installation, but the explicit bar stack now resolves to PowerlineSymbols.

Before the manual installation, those private-use code points collided: rendering the installed OpenSymbol
font shows mathematical Greek symbols (including a summation sign at E0B2), not
Powerline triangles. Fontconfig charset coverage alone is insufficient evidence
that the intended glyph is present. The temporary visual-audit image was local evidence and is not part of this
repository.

The installed package is **fonts-powerline**, a dedicated
symbols font, not a full patched/Nerd Font. Local apt metadata lists Ubuntu
2.8.3-5, 26 KiB installed and a 5,830-byte package, depending on fontconfig.
The user installed it. Pango shaping verified that the explicit bar stack selects
Noto Sans Mono 9 for text and PowerlineSymbols Medium 9 for U+E0B2. Plain Noto
still falls back to OpenSymbol, so explicit fallback is necessary. Baseline/height
joins remain a visual acceptance check; font presence alone does not guarantee
seamless geometry.

**Font Awesome is not required.** This theme declares its own separator and
does not import `awesome-fonts` or any iconset. VOL, WiFi and BAT stay textual.
Powerline separator coverage and Font Awesome module icons are separate concerns.

## Semantic palette

| Module/state | Foreground | Background |
|---|---|---|
| Volume (including while muted) | #e0e6e7 | #46565b |
| Mute normal | #c8d1d5 | #182326 |
| Mute muted / Wi-Fi off | #657f91 | #182124 |
| Wi-Fi connected | #11191c | #6f9291 |
| Wi-Fi disconnected | #c8d1d5 | #46565b |
| Wi-Fi connecting | #a39a76 | #182326 |
| Audio/Wi-Fi query failure | #11191c | #9b6b6b |
| Battery healthy | #8aa3a5 | #182326 |
| Battery charging/full/AC | #11191c | #6f9291 |
| Battery warning | #11191c | #a39a76 |
| Battery critical | #11191c | #b77d7d |
| Battery unknown | #b77d7d | #24191b |
| Date | #c8d1d5 | #182124 |
| Clock | #e0e6e7 | #11191c |

Theme prefixes remove literal `|` from Wi-Fi/date/clock and change `| BAT` to
`BAT`; geometric separators replace those bars. Wi-Fi and date/time behavior
are unchanged. Battery warning/critical use native state-specific suffixes
`LOW`/`CRIT` in addition to the entire yellow/red segment fill. Renderer fixtures
verify these work with the existing built-in battery module and `decorate=false`.
No replacement battery module or unsupported formatting is used.

One `mm_audio` module exposes two named widgets, `volume` and `mute`, with one
shared `(percent, muted)` snapshot and one bounded wpctl read per refresh.
Volume always displays its percentage, even while muted; its left click is a
no-op and wheel up/down sends ±2% with `--limit 1.0`. The mute widget displays
MUTE/MUTED, toggles only on left click and consumes both wheel directions without
changing volume or falling through to the engine's workspace-wheel bindings.
Each widget owns its click registrations and Powerline separator. Query/action
failures safely show VOL ? / MUTE ? and recover on later refreshes. No additional
audio dependency or extra polling module is introduced.

The installed battery module uses strict `<` comparisons. The production config
sets `battery.warning=21` and `battery.critical=11` for inclusive ≤20% / ≤10%
boundaries (21–100 normal). Both fixture suites test the config directly without
CLI threshold overrides. Requested boundaries 21, 20, 11, 10 and 5 are covered.
As in the built-in module, low-charge warnings apply while discharging; charging
and full states retain their teal treatment.

Intended normal bar (colors connect; these are not isolated rectangles):

```text
 VOL 80%  MUTE  WiFi Example WiFi 57%  BAT 74%  Thu 08 Oct  13:40
  slate     dark     teal                      dark teal   dark slate   bar-dark
```

## Safe staged preview

From the repository, run `./scripts/preview-powerline-status` with **stdin kept
open** (a terminal or a supervising subprocess with `stdin=PIPE`). EOF otherwise
causes the installed engine's input loop to redraw rapidly. Ctrl-C or SIGTERM
stops the preview and removes its temporary HOME. Protocol stdout is untouched.

The helper re-execs the permanent venv's Python, checks exactly 2.3.0, and calls
the installed engine's main function with the existing staged config/modules.
A temporary HOME exposes staged modules/themes at the loader's exact user paths.
It discovers the new theme **by name**, preserves stdin, reads live audio and
cached Wi-Fi (`--rescan no`), and uses temporary runtime/cache locations. Python
bytecode writes are disabled. It writes no live config/local files.

For preview safety only, click delivery and the command-socket thread are
disabled in the preview process. `click_events` remains true, and the production
handlers are still registered and tested separately against mocks. Preview
clicks cannot change audio/Wi-Fi/workspaces, launch settings/calendars or control
other processes. This is a protocol/theme preview, not an interaction test.

The script remains development-only and is not deployed to `~/.local/bin`.
The symbols font is installed and explicit fallback is verified. Real i3bar
appearance has since been accepted by the owner. A recreated installation still
needs its own visual and interaction checks in the actual session.

## Validation

```bash
python3 -B -m unittest discover -s tests -v
~/.local/share/venvs/bumblebee-status/bin/python -B tests/validate_powerline.py
python3 -B tests/integration_status.py ~/.local/share/venvs/bumblebee-status
git diff --check
```

The second command uses the actual pinned theme/module/output APIs with 20 mocked
state/boundary frames, tests named discovery, six-control order, decorator joins,
foreground/background overrides, text-only labels and independent click handlers.
It also starts the staged helper against fake read-only wpctl/nmcli commands,
keeps stdin open, validates the i3bar header/JSON, checks multiple frames and
preview click suppression, and verifies clean termination. It never exercises
live controls. The read-only helper omits the unnecessary command socket so the
known sandbox bind restriction does not obscure its protocol validation. The
full integration suite similarly probes Unix-socket availability and skips only
the unused command listener via a temporary, test-only sitecustomize when binds
are denied. Stdin handlers, polling, renderer, synthetic controls, timeout/error
recovery and resource checks use the real installed engine. The skip is reported
explicitly and no production code or environment is patched by that test.

Full-height separator geometry, baseline alignment and actual i3bar rendering
were accepted manually on the reference installation. Verify those properties
and font fallback again when recreating the setup on another machine.
