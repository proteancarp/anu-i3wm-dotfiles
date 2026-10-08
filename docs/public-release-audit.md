# anu-i3wm-dotfiles — public-release audit

Visual theme: **Mountain Mist v2**. Audit date: 2026-10-08.

**Current-tree verdict: READY for a fresh public root commit.** Original work
now has an MIT license, required i3 BSD notices are retained, and the current
file contents have been sanitized. The existing six-commit history still
contains private metadata/content and is not approved for publication.
No commit, history rewrite, deployment or GitHub publication was made.

## Scope and method

Reviewed the complete working tree, tracked file modes, all six reachable
commits and 52 unique file-content blobs across all refs/reflogs, commit metadata,
historical path inventory and repository-local Git configuration. `git fsck`
reported no additional dangling/unreachable objects. No remote is configured.
The repository contains text files only, with no wallpaper, image, binary,
downloaded package, environment or cache tracked in current or inspected history.

Searches covered private-key headers, common token formats, credential-bearing
URLs, secret assignments, emails, home paths, username/hostname, SSIDs, MAC/IP
addresses, UUIDs, backup paths and temporary/session identifiers. Reviewed matches
distinguish fixture data and credential-handling descriptions from actual secrets.
Dedicated gitleaks/trufflehog scanners were unavailable; nothing was installed.
This is a local pattern/source review, not a guarantee against every possible
secret format or material outside this repository.

## Findings and classifications

| Occurrence | Classification | Result / action |
| --- | --- | --- |
| Passwords, API keys, tokens, cookies, SSH/private keys, Wi-Fi credentials or other authentication material | No actual material found | References to secrets/passwords describe safe handling or deliberate mock error output; no credentials are read or embedded. |
| Personal author/committer email in all six commits (12 metadata fields) | SHOULD BE REMOVED BEFORE PUBLICATION unless explicitly accepted | Not reproduced here. Choose a public identity/noreply email and a separate reviewed history rewrite or sanitized publication history. Changing future Git config or current files cannot remove old metadata. |
| Real local SSID in the latest committed Powerline doc/fixtures | SHOULD BE GENERALIZED | Replaced in the working tree with `Example WiFi`; old committed versions still contain it. Sanitize history or explicitly accept disclosure before publishing existing history. |
| Machine-style wireless interface in Powerline fixtures | SHOULD BE GENERALIZED | Replaced with synthetic `wlan-test`; real queries still discover their interface. |
| Exact initial backup timestamp and ephemeral image location in docs | SHOULD BE GENERALIZED | Replaced with a timestamp placeholder / description of local-only evidence. No backup files are included. |
| Historical lab timezone/location | SHOULD BE GENERALIZED | Removed from the current introduction; older documentation blobs retain it. Include it in the history privacy review if publishing that history. |
| Owner name within requested `anu-i3wm-dotfiles` project name | SAFE AND INTENTIONAL | Explicitly requested public project name; no literal private home path is present. |
| Existing `proteancarp` author alias in config comments/history | SAFE AND INTENTIONAL | Attribution/pseudonym rather than an operational hostname or project name; preserve unless the owner chooses a different public identity. |
| Private home path/hostname, private URLs, real MAC/IP/device UUIDs or session IDs | No occurrences found | No replacement required. |
| `AA:BB:CC:DD:EE:FF`, `12345678-1234-1234-1234-123456789abc`, example SSIDs/interfaces | SAFE AND INTENTIONAL | Synthetic tests, including escaped-field and action-routing coverage; not device identifiers. |
| `1.1.1.1` in the historical compatibility report | SAFE AND INTENTIONAL | Public address described in upstream module analysis; not a private network address or a new probe. |
| `/tmp/.bumblebee-status.{proc.pid}` in integration testing | SAFE AND INTENTIONAL | Upstream socket convention with dynamically obtained test PID, not an archived session ID. |
| `$HOME`, `~`, environment-derived paths, `/sys/class/power_supply/BAT0`, `BAT0` | SAFE AND INTENTIONAL | Supported runtime conventions and documented battery preference with startup auto-detection fallback. |
| Dates/version/source commit IDs and public upstream documentation URLs | SAFE AND INTENTIONAL | Reproducibility evidence, not local connection UUIDs or authentication links. |

## Portability and documentation

README and INSTALL now consistently identify the repository as
`anu-i3wm-dotfiles` and the theme as Mountain Mist v2. Earlier implementation/lab
documents are marked historical; README/INSTALL describe the accepted six-widget
bar, shared audio query, inclusive thresholds, hidden tray, Powerline fallback,
Rofi behavior and current launcher override accurately.

Home paths already use shell expansion or Python environment-derived paths where
supported. No blind application-specific replacements were necessary. The lock
binary and wallpaper are still external prerequisites at documented home-relative
paths. Mint-specific bindings, secret-agent/PAM setup, audio stack, locale and
startup ownership must be reviewed on another host. Legacy pactl/i3status media-key
refresh remains known technical debt, not silently changed in this release audit.

The new `.gitignore` covers Python caches/venvs, local state/backups, temporary
integration output, logs, secret containers, downloaded packages, build output,
and editor debris. It does not ignore `.config` or production `.local` files.
All five production entry points (lock.sh and four bin helpers) plus the staged
preview have Git executable mode 100755. Tests are invoked through Python.

## Licensing and assets

The owner authorized **MIT for original helpers, configuration additions and
documentation**. [LICENSE](../LICENSE) uses the public copyright identity
`anu-i3wm-dotfiles contributors`; it does not claim ownership of third-party
work. See the [OSI MIT text](https://opensource.org/license/mit).

The i3 file is explicitly derived from i3-config-wizard. Installed i3 package
copyright metadata identifies BSD-3-Clause. Comparison with the installed sample
found 110 identical lines in the current config; attribution is retained in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md), including the copyright,
conditions and disclaimer. It contains only the i3 notice applicable to shipped
content; Debian packaging, separately installed dependencies and fonts are not
vendored. Dependencies and fonts are
installed separately and retain their own licenses; no copies are vendored.

No assets are included. The external mountain wallpaper's ownership/license is
unknown: do not add it or a screenshot reproducing it until redistribution rights
are established. Use an owned/licensed replacement or keep it external. The
external i3lock-color source/binary is likewise not bundled.

## Fresh-history publication boundary

The current file tree can be used as the root of a fresh public history. Include
the production files, docs, tests, preview script, `.gitignore`, LICENSE and
THIRD_PARTY_NOTICES; exclude the existing `.git` directory and all ignored local
output. A future root commit needs a deliberately public author/committer identity
(such as the owner's GitHub noreply identity). No commit or Git identity change
was performed here.

Do not push the existing branches/tags or copy their Git objects into that fresh
repository. Current-tree sanitization does not erase personal email, SSID or
location data in the old commits. Publishing the old history would require a
separately authorized privacy review/rewrite. Recheck the exact new root commit
and refs before any push. External asset rights remain outside this license.

Validation: 53 unit tests, 20 real-renderer Powerline state/boundary fixtures,
staged preview and Bumblebee 2.3.0 integration pass with fake control tools.
Static checks cover i3/Rofi, shell/Python, JSON/INI, native Picom/Kitty parsing,
desktop entry, Pango glyph selection and `git diff --check`. Dunst native X
initialization, command-socket binding and real GUI/security operations remain
outside sandbox verification, as documented in README. No live files changed.
