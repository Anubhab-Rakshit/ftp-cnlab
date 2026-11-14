"""
Colorized terminal packet inspector and logger for FTP operations.
Displays raw NVT/ASCII wire packets and data channel events.
"""

import sys
import time
from datetime import datetime


class WireLogger:
    """Terminal visualizer for wire-level NVT/ASCII and data transfer activity."""

    # ANSI Color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    def __init__(self, prefix: str = "FTP", show_wire: bool = True):
        self.prefix = prefix
        self.show_wire = show_wire

    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def ctrl_recv(self, raw_str: str, client_id: str = ""):
        """Logs incoming NVT/ASCII control command."""
        if not self.show_wire:
            return
        cid = f"[{client_id}] " if client_id else ""
        disp = repr(raw_str)
        print(f"{self.DIM}{self._now()}{self.RESET} {self.CYAN}[CTRL:RECV]{self.RESET} {cid}<-- {self.BOLD}{disp}{self.RESET}")
        sys.stdout.flush()

    def ctrl_send(self, raw_str: str, client_id: str = ""):
        """Logs outgoing NVT/ASCII control response."""
        if not self.show_wire:
            return
        cid = f"[{client_id}] " if client_id else ""
        disp = repr(raw_str)
        print(f"{self.DIM}{self._now()}{self.RESET} {self.GREEN}[CTRL:SEND]{self.RESET} {cid}--> {self.BOLD}{disp}{self.RESET}")
        sys.stdout.flush()

    def data_event(self, event_type: str, message: str, client_id: str = ""):
        """Logs data connection events (ESTB, STRM, CLSE)."""
        cid = f"[{client_id}] " if client_id else ""
        print(f"{self.DIM}{self._now()}{self.RESET} {self.MAGENTA}[DATA:{event_type}]{self.RESET} {cid}{message}")
        sys.stdout.flush()

    def info(self, message: str):
        print(f"{self.DIM}{self._now()}{self.RESET} {self.BLUE}[INFO]{self.RESET} {message}")
        sys.stdout.flush()

    def success(self, message: str):
        print(f"{self.DIM}{self._now()}{self.RESET} {self.GREEN}{self.BOLD}[SUCCESS]{self.RESET} {message}")
        sys.stdout.flush()

    def warn(self, message: str):
        print(f"{self.DIM}{self._now()}{self.RESET} {self.YELLOW}[WARN]{self.RESET} {message}")
        sys.stdout.flush()

    def error(self, message: str):
        print(f"{self.DIM}{self._now()}{self.RESET} {self.RED}{self.BOLD}[ERROR]{self.RESET} {message}")
        sys.stdout.flush()

