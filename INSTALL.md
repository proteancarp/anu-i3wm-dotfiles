# Installing anu-i3wm-dotfiles

These instructions install the **Mountain Mist v2** theme from **anu-i3wm-dotfiles**
on another Linux Mint X11/i3 machine. They were **not executed as part of the final documentation
audit**. Review machine-specific paths and back up existing files first. The
current repository is accepted v2; see [README.md](README.md) for behavior.

Original work is [MIT-licensed](LICENSE). Retain the
[third-party i3 notices](THIRD_PARTY_NOTICES.md) when redistributing the inherited
configuration. External dependencies and assets retain their own licenses.

## Packages and host prerequisites

The reference machine uses Python 3.12.3, i3 4.23, Rofi 1.7.5, Picom 10.2,
Dunst 1.9.2, Kitty 0.32.2, NetworkManager 1.46, and WirePlumber 0.4.17.
Only Bumblebee is runtime-pinned; different distro versions need revalidation.

| Requirement | Mint/Ubuntu packages |
| --- | --- |
| WM and legacy fallback | `i3-wm i3status` |
| Menus, compositor, notifications, terminal | `rofi picom dunst kitty` |
| Session startup, wallpaper, sleep locking | `dex feh xss-lock` |
| Fonts | `fonts-noto-mono fonts-dejavu-core fonts-powerline` |
| Python environment | `python3 python3-venv` (venv supplies pip) |
| Repository/source checkout | `git` |
| Existing audio stack / `wpctl` | PipeWire with `wireplumber`; `pipewire-pulse pulseaudio-utils` for retained pactl media keys |
| Existing network stack / editor | `network-manager network-manager-gnome` |
| Optional retained application bindings | `nemo gnome-screenshot`, Mint's `cinnamon-settings` |

For a Mint host already running NetworkManager and PipeWire/WirePlumber, an
example UI package installation is:

```sh
sudo apt install i3-wm i3status rofi picom dunst kitty dex feh xss-lock \
  fonts-noto-mono fonts-dejavu-core fonts-powerline python3 python3-venv git \
  network-manager-gnome pulseaudio-utils
```

Do not use a rice installation to migrate an existing audio/network stack
implicitly. Confirm `wpctl`, `nmcli`, `nm-connection-editor`, a working session
D-Bus, and the usual Mint authentication/secret agent. Hidden tray icons do not
replace or disable that infrastructure. No Font Awesome, Nerd Font, pamixer,
pulsectl, Tk or optional Python `power` package is needed.

### External wallpaper and locker

Provide `~/Pictures/wallpapers/mountain.png`, or edit both feh's i3 startup
command and lock.sh's image path before installation. No wallpaper is shipped.

Provide a compatible i3lock-color binary at
`~/Downloads/i3lock-color/build/i3lock`, or adapt lock.sh's explicit path.
Installing stock `i3lock` alone is insufficient. The reference source checkout
is Raymo111/i3lock-color commit
`e6c0caf9b7aa22cc7864493132a1a2e258da1761`, whose build reports
`2.13.c.5-7-ge6c0caf (2025-12-11)`.

For a matching local source build, install the build dependencies documented
by that checkout (autoconf/automake, compiler, make, pkg-config, PAM, Cairo,
Fontconfig, libev, X11/XCB/XKB, JPEG and GIF development libraries), then:

```sh
git clone https://github.com/Raymo111/i3lock-color.git ~/Downloads/i3lock-color
git -C ~/Downloads/i3lock-color checkout e6c0caf9b7aa22cc7864493132a1a2e258da1761
(cd ~/Downloads/i3lock-color && ./build.sh)
```

The repository does not supply/install PAM policy. Check the host's i3lock PAM
configuration and actual password authentication. Preserve `exec --nofork` and
the inherited sleep-lock descriptor; validate lock, failed password feedback,
unlock and suspend/wake in the real session before relying on sleep protection.
Session idle/DPMS timing is configured separately by the host.

## Create the permanent Bumblebee environment

```sh
python3 -m venv "$HOME/.local/share/venvs/bumblebee-status"
"$HOME/.local/share/venvs/bumblebee-status/bin/python" -m pip install 'bumblebee-status==2.3.0'
"$HOME/.local/share/venvs/bumblebee-status/bin/python" -m pip check
"$HOME/.local/share/venvs/bumblebee-status/bin/python" -c \
  'import importlib.metadata; assert importlib.metadata.version("bumblebee-status") == "2.3.0"'
```

Confirm that `share/bumblebee-status/themes/default.json` and
`share/bumblebee-status/themes/icons/ascii.json` exist inside the venv. The
production wrapper sets `XDG_DATA_DIRS`; directly running the bare venv entry
point can fail to discover the default theme. No activation shell is required.

## Verify fonts and staged configuration

```sh
fc-match 'Noto Sans Mono'
fc-match 'Noto Sans Mono,PowerlineSymbols:charset=e0b2' -f '%{family}\n%{file}\n'
```

The second result must be `PowerlineSymbols`, normally
`/usr/share/fonts/opentype/PowerlineSymbols.otf`, rather than OpenSymbol. Keep
the explicit **bar-only** `font pango:Noto Sans Mono, PowerlineSymbols 9`.
Fontconfig coverage alone cannot prove the correct private-use glyph: verify
the actual left triangle and joins in i3bar after activation.

From the repository root, before copying:

```sh
XDG_RUNTIME_DIR=/tmp i3 -C -c .config/i3/config
for theme in config network calendar powermenu; do
  XDG_CONFIG_HOME="$PWD/.config" rofi -rasi-validate "$PWD/.config/rofi/$theme.rasi" || exit 1
done
bash -n .config/i3/lock.sh .local/bin/mountain-mist-status .local/bin/powermenu
python3 -B -m unittest discover -s tests -v
~/.local/share/venvs/bumblebee-status/bin/python -B tests/validate_powerline.py
python3 -B tests/integration_status.py ~/.local/share/venvs/bumblebee-status
git diff --check
```

Ensure `C.UTF-8` is available for the configured English date/time output
(`locale -a` may list its equivalent as `C.utf8`). Audit the launcher-selected
battery on hosts without BAT0; automatic startup detection is supported, but
hot removal and multiple batteries need a real hardware check.

Review host autostart entries for duplicate Picom, xss-lock or notification
daemons. Do not start a second compositor to test config parsing.

## Back up and copy production files

Copies are recommended: they keep deployed behavior independent of repository
edits. This explicit allowlist excludes documentation, tests, previews and
temporary environments. Run it from the repository root. It creates a complete
snapshot **before any overwrite**, records absent files, copies production
files, and assigns 0755 to entry points and 0644 to data/modules.

```sh
python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, stat

repo, home = Path.cwd(), Path.home()
paths = '''
.config/i3/config
.config/i3/lock.sh
.config/i3status/config
.config/bumblebee-status/config
.config/bumblebee-status/modules/mm_audio.py
.config/bumblebee-status/modules/mm_wifi.py
.config/bumblebee-status/themes/mountain-mist.json
.config/bumblebee-status/themes/mountain-mist-powerline.json
.config/rofi/config.rasi
.config/rofi/network.rasi
.config/rofi/calendar.rasi
.config/rofi/powermenu.rasi
.config/picom/picom.conf
.config/autostart/picom.desktop
.config/dunst/dunstrc
.config/kitty/kitty.conf
.local/bin/mountain-mist-status
.local/bin/rofi-network
.local/bin/rofi-calendar
.local/bin/powermenu
.local/lib/mountain_mist/__init__.py
.local/lib/mountain_mist/runtime.py
.local/lib/mountain_mist/network.py
.local/lib/mountain_mist/calendar_view.py
'''.split()
for rel in paths:
    src, dst = repo / rel, home / rel
    assert src.is_file(), f'Missing source: {src}'
    assert not any(p.is_symlink() for p in [dst, *dst.parents] if p != home), f'Symlink: {dst}'
    assert not dst.exists() or dst.is_file(), f'Not a file: {dst}'
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-install')
backup = home / '.local/state/mountain-mist/backups' / stamp
backup.mkdir(parents=True, exist_ok=False)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows = []
for rel in paths:
    dst, saved = home / rel, backup / rel
    existed = dst.exists()
    row = dict(original_path=str(dst), original_existed=existed,
               backup_path=str(saved) if existed else None,
               original_sha256=digest(dst) if existed else None,
               original_mode=oct(stat.S_IMODE(dst.stat().st_mode)) if existed else None)
    if existed:
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, saved)
        assert digest(saved) == row['original_sha256']
    rows.append(row)
manifest = backup / 'manifest.json'
manifest.write_text(json.dumps(dict(files=rows), indent=2) + '\n')
print('Backup manifest:', manifest, flush=True)
for rel in paths:
    src, dst = repo / rel, home / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    mode = 0o755 if rel.startswith('.local/bin/') or rel == '.config/i3/lock.sh' else 0o644
    dst.chmod(mode)
    assert digest(dst) == digest(src)
    assert stat.S_IMODE(dst.stat().st_mode) == mode
print('Installed and verified', len(paths), 'production files; i3 was not reloaded.')
PY
```

Keep backup manifests private and intact. For later refinements, snapshot only
affected files in a new supplemental directory; never rewrite the original
history. Backups cover files, not package/service changes or the external
locker/wallpaper. Do not copy the entire repository into your home directory.

Symlinking is an alternative for users who deliberately want repository edits
to become live immediately. Back up existing files **and link targets** first,
keep the checkout in a permanent location, and link only the allowlisted paths.
Keep `.local/bin` and `.local/lib` paired: helpers resolve shared imports from
their real file locations. The copy/restore examples here reject symlinks so
they cannot accidentally overwrite a checkout or an external target. Adapting
them requires explicit link-aware backup/restore handling.

For manual helper commands, ensure `~/.local/bin` is in your shell PATH. i3's
status and helper click commands already use explicit paths.

## Activation and session expectations

The installed i3 config selects Bumblebee and hides the tray. Copying files
does not activate them. Validate the live config with
`XDG_RUNTIME_DIR=/tmp i3 -C -c ~/.config/i3/config` before a deliberate reload.

For the first installation, choose i3 in the login manager and use a fresh
login so the plain `exec` startup entries launch once. An i3 reload applies
config/bar settings but does not launch those startup entries; an in-place
restart is not a substitute for a fresh login for that purpose. Avoid duplicate
daemons. Kitty's existing windows and other apps may need their own config
reload/relaunch; replacing files alone does not restart them.

When ready, `i3-msg reload` applies bar configuration. A changed backend command
or bar recreation starts a new status process. If only module/theme file
contents changed, confirm the backend was relaunched; an unchanged command can
keep the old process. A full i3 restart is not intrinsically required for a
backend update, but loaded Python modules/themes need a new backend process.

Inspect actual glyphs, spacing, menu cancellation and state colors before
testing controls. Keep stdin open for any standalone backend run; piping it
from `/dev/null` triggers an upstream EOF redraw defect. The development-only
`scripts/preview-powerline-status` preserves stdin and suppresses click actions.

## Rollback

Each manifest restores exactly its scope. Review it first, verify saved
checksums, then restore prior files/modes or remove targets that were originally
absent. For multiple updates, apply supplemental manifests **newest first**,
then the initial manifest if returning to the pre-install setup. Do not infer
the desired state from only the latest backup.

Example restoration (replace the manifest argument; this writes live files):

```sh
python3 - "$HOME/.local/state/mountain-mist/backups/<timestamp>/manifest.json" <<'PY'
from pathlib import Path
import hashlib, json, shutil, sys
rows = json.loads(Path(sys.argv[1]).read_text())['files']
home = Path.home().resolve()
for row in rows:
    dst = Path(row['original_path'])
    assert dst.is_relative_to(home), dst
    assert not any(p.is_symlink() for p in [dst, *dst.parents] if p != home), dst
    if row['original_existed']:
        saved = Path(row['backup_path'])
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == row['original_sha256']
for row in rows:
    dst = Path(row['original_path'])
    if row['original_existed']:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row['backup_path'], dst)
        if row.get('original_mode'):
            dst.chmod(int(row['original_mode'], 8))
    else:
        dst.unlink(missing_ok=True)
print('Manifest restored; no reload performed.')
PY
XDG_RUNTIME_DIR=/tmp i3 -C -c "$HOME/.config/i3/config"
# Only after validation and an intentional decision to activate rollback:
i3-msg reload
```

On an existing installation, the immutable initial manifest is under
`~/.local/state/mountain-mist/backups/<initial-timestamp>/manifest.json`.
Later directories may have descriptive suffixes; `*-prepare-powerline-preview`
predates Powerline, while `*-audio-battery-refinement` restores only the prior
audio/battery version. These are local history, not files included in the repo.

For a **flat-theme-only fallback** while retaining v2 functionality, back up
the current launcher/config and change BOTH selections:

```text
~/.config/bumblebee-status/config:
    theme = mountain-mist
~/.local/bin/mountain-mist-status:
    STATUS_THEME="$HOME/.config/bumblebee-status/themes/mountain-mist.json"
```

Optionally restore the previous bar font (`font pango:Noto Sans Mono 9`) if
returning to the exact pre-Powerline appearance. Validate and deliberately
relaunch the bar backend/reload i3; no package removal is required. A historical
pre-Powerline rollback needs the corresponding backups, rather than mixing
old audio code with new config/theme. To return to i3status, restore the backed-up
i3 config (or deliberately select `status_command i3status -c ~/.config/i3status/config`)
and ensure the retained i3status config exists. Restoring files does not itself
stop/start services; session startup changes need the appropriate fresh login.
