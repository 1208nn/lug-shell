"""终端底座：raw 输入、替换屏幕、尺寸和 shell 风格按键解析。"""

from __future__ import annotations

import os
import re
import select
import shutil
import sys
import termios

CSI_ARROWS = {b"A": "up", b"B": "down", b"C": "right", b"D": "left",
              b"H": "home", b"F": "end"}
TILDE = {b"1": "home", b"7": "home", b"4": "end", b"8": "end",
         b"3": "delete", b"2": "insert"}
CTRL = {0x01: "ctrl-a", 0x02: "ctrl-b", 0x03: "ctrl-c", 0x04: "ctrl-d",
        0x05: "ctrl-e", 0x06: "ctrl-f", 0x0B: "ctrl-k", 0x0C: "ctrl-l",
        0x0E: "ctrl-n", 0x10: "ctrl-p", 0x11: "ctrl-q", 0x12: "ctrl-r",
        0x15: "ctrl-u", 0x17: "ctrl-w"}


class Terminal:
    def __init__(self):
        self.fd_in = sys.stdin.fileno()
        self.fd_out = sys.stdout.fileno()
        self.old = None
        self._entered = False
        self._inbuf = b""

    def __enter__(self):
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("需要一个真正的终端（TTY）才能玩。")
        self.old = termios.tcgetattr(self.fd_in)
        new = termios.tcgetattr(self.fd_in)
        new[0] &= ~(termios.IXON | termios.IXOFF)
        new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd_in, termios.TCSADRAIN, new)
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J\x1b[H")
        self.flush()
        self._entered = True
        return self

    def __exit__(self, *exc):
        if self._entered:
            self.write("\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l")
            self.flush()
            try:
                termios.tcsetattr(self.fd_in, termios.TCSADRAIN, self.old)
            except termios.error:
                pass
            self._entered = False
        return False

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def size(self) -> tuple[int, int]:
        s = shutil.get_terminal_size(fallback=(100, 30))
        return s.columns, s.lines

    def clear(self) -> None:
        self.write("\x1b[2J\x1b[H")

    def _parse(self, data: bytes) -> list[str]:
        buf = self._inbuf + data
        keys: list[str] = []
        i = 0
        while i < len(buf):
            b = buf[i]
            if b == 0x1B:
                if i + 1 >= len(buf):
                    keys.append("esc")
                    i += 1
                    continue
                if buf[i + 1] == 0x5B:  # [
                    m = re.match(rb"\x1b\[([0-9;]*)([A-Za-z~])", buf[i:])
                    if not m:
                        if len(buf) - i < 8:
                            self._inbuf = buf[i:]
                            return keys
                        keys.append("esc")
                        i += 1
                        continue
                    params, final = m.group(1), m.group(2)
                    if final in CSI_ARROWS:
                        name = CSI_ARROWS[final]
                        if b";5" in params or params == b"5":
                            name = "ctrl-" + name
                        keys.append(name)
                    elif final == b"Z":
                        keys.append("tab")
                    elif final == b"~":
                        num = params.split(b";")[0]
                        if num in TILDE:
                            keys.append(TILDE[num])
                    i += m.end()
                    continue
                if buf[i + 1] == 0x4F:  # O
                    m = re.match(rb"\x1bO([A-Za-z])", buf[i:])
                    if m:
                        final = m.group(1)
                        if final in CSI_ARROWS:
                            keys.append(CSI_ARROWS[final])
                        i += m.end()
                        continue
                keys.append("esc")
                i += 1
                continue
            if b in CTRL:
                keys.append(CTRL[b])
                i += 1
                continue
            if b in (0x0A, 0x0D):
                keys.append("enter")
            elif b in (0x08, 0x7F):
                keys.append("backspace")
            elif b == 0x09:
                keys.append("tab")
            elif 0x20 <= b <= 0x7E:
                keys.append(chr(b))
            i += 1
        self._inbuf = b""
        return keys

    def read_keys(self, timeout: float) -> list[str]:
        if self._inbuf:
            keys = self._parse(b"")
            if keys:
                return keys
        ready, _, _ = select.select([self.fd_in], [], [], max(0.0, timeout))
        if not ready:
            return []
        try:
            data = os.read(self.fd_in, 4096)
        except OSError:
            return []
        if not data:
            return []
        return self._parse(data)
