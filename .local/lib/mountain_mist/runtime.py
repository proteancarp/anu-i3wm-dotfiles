"""Bounded processes and Rofi input; never use the status bar's stdin."""

from contextlib import contextmanager
import fcntl
import html
import os
from pathlib import Path
import signal
import subprocess
import time
import unicodedata


class CommandError(RuntimeError):
    """A diagnostic without command arguments, output, or credentials."""


def _stop(proc):
    # Descendants may hold a pipe open after their parent exits.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=0.3)
            # A descendant could close its pipes but ignore TERM; it still
            # belongs to this timed-out command's process group.
            if sig == signal.SIGTERM:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return
        except subprocess.TimeoutExpired:
            continue
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream:
            stream.close()
    # poll() reaps an exited child without an unbounded wait.
    proc.poll()


def run(argv, timeout=2, input_text=None, check=True):
    """Run argv with a deadline, isolated stdin, and bounded group cleanup."""
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    try:
        proc = subprocess.Popen(
            list(argv), stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace', env=env, start_new_session=True,
        )
    except OSError as exc:
        raise CommandError(f'{Path(argv[0]).name}: unavailable') from exc
    try:
        out, _ = proc.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _stop(proc)
        raise CommandError(f'{Path(argv[0]).name}: timed out') from exc
    except BaseException:
        _stop(proc)
        raise
    if check and proc.returncode:
        raise CommandError(f'{Path(argv[0]).name}: failed ({proc.returncode})')
    return subprocess.CompletedProcess(argv, proc.returncode, out, '')


def label(text, limit=48):
    """Plain menu/bar text, stripped of controls (including Rofi's NUL syntax)."""
    clean = ''.join(c for c in text if not unicodedata.category(c).startswith('C'))
    return clean if len(clean) <= limit else clean[:limit - 1] + '…'


class Deadline:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def run(self, argv, timeout=2, **kwargs):
        remaining = self.end - time.monotonic()
        if remaining <= 0:
            raise CommandError('helper: time limit reached')
        return run(argv, timeout=min(timeout, remaining), **kwargs)


def choose(rows, prompt, theme, message='', runner=run):
    result = runner(
        ['rofi', '-dmenu', '-no-custom', '-format', 'i', '-p', prompt,
         '-theme', str(theme), '-mesg', html.escape(message)],
        timeout=300, input_text='\n'.join(label(row, 96) for row in rows) + '\n', check=False,
    )
    if result.returncode:
        return None
    try:
        index = int(result.stdout.strip())
    except ValueError:
        return None
    return index if 0 <= index < len(rows) else None


@contextmanager
def menu_lock(name):
    base = Path(os.environ.get('XDG_RUNTIME_DIR') or
                os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    directory = base / 'mountain-mist'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(directory / (name + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
        else:
            yield True
    finally:
        os.close(fd)


def helper_signals():
    def stop(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)


def start_helper(name):
    """Helpers supervise their own lifetime and never inherit i3bar streams."""
    return subprocess.Popen(
        [str(Path.home() / '.local/bin' / name)], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
