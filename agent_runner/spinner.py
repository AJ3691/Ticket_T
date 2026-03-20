"""
spinner.py — Animated terminal spinner for showing progress.

Runs in a background thread on stderr so it doesn't interfere with
subprocess stdout output. Use as a context manager:

    with Spinner("Running [core] add_strategy"):
        result = subprocess.run(...)
"""

import itertools
import sys
import threading
import time


class Spinner:
    FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, message: str = "Working"):
        self.message = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            sys.stderr.write(f"\r{frame}  {self.message}...")
            sys.stderr.flush()
            time.sleep(0.12)
        # clear the spinner line
        sys.stderr.write("\r" + " " * (len(self.message) + 15) + "\r")
        sys.stderr.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
