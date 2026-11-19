"""shell 行编辑、终端滚动区、回合逻辑和待机脚本。"""

from __future__ import annotations

import random
from dataclasses import dataclass

from canvas import (
    AMBER, BG, DIM, FAINT, GREEN, INK, RED, TEAL, WHITE,
    Canvas, twidth,
)
from missions import (
    DIM as M_DIM, ERR as M_ERR, OK as M_OK, OUT as M_OUT,
    PATH as M_PATH, WARN as M_WARN, Mission, Step, pick_missions,
)

ROUND_TIME = 75.0
MISSION_COUNT = 5

COLOR = {
    M_OK: GREEN,
    M_OUT: INK,
    M_DIM: FAINT,
    M_ERR: RED,
    M_WARN: AMBER,
    M_PATH: TEAL,
}

USER = GREEN
CWD = TEAL
INPUT = WHITE
PROMPT = (GREEN, TEAL)


def wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return [""]
    if not text:
        return [""]
    out: list[str] = []
    line = ""
    used = 0
    for ch in text:
        w = twidth(ch)
        if used + w > width:
            out.append(line)
            line, used = "", 0
        line += ch
        used += w
    out.append(line)
    return out


@dataclass
class Line:
    text: str
    color: tuple[int, int, int] = INK
    bold: bool = False


class Editor:
    def __init__(self):
        self.buffer = ""
        self.cursor = 0
        self.history: list[str] = []
        self.hist_pos: int | None = None
        self.draft = ""

    def clear(self) -> None:
        self.buffer = ""
        self.cursor = 0
        self.hist_pos = None
        self.draft = ""

    def insert(self, ch: str) -> None:
        self.buffer = self.buffer[:self.cursor] + ch + self.buffer[self.cursor:]
        self.cursor += len(ch)

    def backspace(self) -> None:
        if self.cursor > 0:
            self.buffer = self.buffer[:self.cursor - 1] + self.buffer[self.cursor:]
            self.cursor -= 1

    def delete(self) -> None:
        if self.cursor < len(self.buffer):
            self.buffer = self.buffer[:self.cursor] + self.buffer[self.cursor + 1:]

    def left(self) -> None:
        self.cursor = max(0, self.cursor - 1)

    def right(self) -> None:
        self.cursor = min(len(self.buffer), self.cursor + 1)

    def home(self) -> None:
        self.cursor = 0

    def end(self) -> None:
        self.cursor = len(self.buffer)

    def word_left(self) -> None:
        i = self.cursor
        while i > 0 and self.buffer[i - 1] == " ":
            i -= 1
        while i > 0 and self.buffer[i - 1] != " ":
            i -= 1
        self.cursor = i

    def word_right(self) -> None:
        i = self.cursor
        n = len(self.buffer)
        while i < n and self.buffer[i] == " ":
            i += 1
        while i < n and self.buffer[i] != " ":
            i += 1
        self.cursor = i

    def kill_word(self) -> None:
        end = self.cursor
        i = end
        while i > 0 and self.buffer[i - 1] == " ":
            i -= 1
        while i > 0 and self.buffer[i - 1] != " ":
            i -= 1
        self.buffer = self.buffer[:i] + self.buffer[end:]
        self.cursor = i

    def kill_start(self) -> None:
        self.buffer = self.buffer[self.cursor:]
        self.cursor = 0

    def kill_end(self) -> None:
        self.buffer = self.buffer[:self.cursor]

    def up(self) -> None:
        if not self.history:
            return
        if self.hist_pos is None:
            self.draft = self.buffer
            self.hist_pos = len(self.history)
        if self.hist_pos > 0:
            self.hist_pos -= 1
            self.buffer = self.history[self.hist_pos]
            self.end()

    def down(self) -> None:
        if self.hist_pos is None:
            return
        self.hist_pos += 1
        if self.hist_pos >= len(self.history):
            self.hist_pos = None
            self.buffer = self.draft
        else:
            self.buffer = self.history[self.hist_pos]
        self.end()

    def submit(self) -> str:
        line = self.buffer.strip()
        if line:
            self.history.append(line)
        self.clear()
        return line

    def complete(self, words: set[str]) -> list[str]:
        start = self.buffer.rfind(" ", 0, self.cursor) + 1
        prefix = self.buffer[start:self.cursor]
        if not prefix:
            return []
        cands = sorted(w for w in words if w.startswith(prefix))
        if not cands:
            return []
        lcp = cands[0]
        for w in cands[1:]:
            while lcp and not w.startswith(lcp):
                lcp = lcp[:-1]
        if len(lcp) > len(prefix):
            self.buffer = self.buffer[:start] + lcp + self.buffer[self.cursor:]
            self.cursor = start + len(lcp)
        if len(cands) == 1:
            pos = start + len(cands[0])
            if self.cursor == pos and self.cursor < len(self.buffer) + 1:
                if self.cursor == len(self.buffer) and not self.buffer.endswith(" "):
                    self.buffer += " "
                    self.cursor += 1
        return cands


class Shell:
    def __init__(self, cwd: str = "~"):
        self.cwd = cwd
        self.log: list[Line] = []
        self.editor = Editor()

    def clear_log(self) -> None:
        self.log.clear()

    def print(self, text: str = "", color=INK, bold: bool = False) -> None:
        self.log.append(Line(text, color, bold))

    def output(self, lines: tuple[tuple[str, str], ...]) -> None:
        for text, color in lines:
            self.print(text, COLOR.get(color, INK))

    def prompt(self) -> str:
        return f"lug@booth:{self.cwd}$ "

    def echo(self, line: str) -> None:
        self.print(self.prompt() + line, WHITE)

    def mission_header(self, mission: Mission, index: int, total: int) -> None:
        self.print("")
        self.print(f"# 任务 {index}/{total} · {mission.title}", AMBER, bold=True)
        self.print(f"# {mission.brief}", INK)
        self.print("# 输入 hint 看提示 · skip 跳过（-10s）", FAINT)

    def mission_step(self, mission: Mission, index: int, total: int) -> None:
        if len(mission.steps) > 1:
            self.print(f"# 步骤 {index}/{total}", TEAL)

    def render(self, c: Canvas, w: int, h: int, input_prompt: str,
               show_cursor: bool = True, input_color=INPUT) -> None:
        area_y = 2
        log_h = max(1, h - 5)
        wrap_w = max(1, w - 2)
        rows: list[Line] = []
        for line in self.log:
            for piece in wrap(line.text, wrap_w):
                rows.append(Line(piece, line.color, line.bold))
        visible = rows[-log_h:]
        for i, line in enumerate(visible):
            c.put(1, area_y + i, line.text, line.color, BG, line.bold)

        iy = h - 2
        c.hline(0, h - 3, w, "─", FAINT, BG)
        prompt = input_prompt
        full = prompt + self.editor.buffer
        avail = max(1, w - 2)
        col = len(prompt) + self.editor.cursor
        start = max(0, col - avail + 1) if len(full) > avail else 0
        if start < len(prompt):
            c.put(1, iy, prompt[start:], GREEN, BG, bold=True)
            input_x = 1 + len(prompt) - start
        else:
            input_x = 1
        buf_start = max(0, start - len(prompt))
        c.put(input_x, iy, self.editor.buffer[buf_start:], input_color, BG, bold=True)
        if show_cursor:
            x = 1 + col - start
            if 1 <= x < w - 1:
                ch = full[col] if 0 <= col < len(full) else " "
                c.cursor(x, iy, ch)


def _generic(line: str, shell: Shell) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """极小的模拟 shell：让输入不只是对着任务表。"""
    low = " ".join(line.strip().split())
    if low in ("pwd",):
        return True, ((f"/home/lug/{shell.cwd[2:]}" if shell.cwd != "~" else "/home/lug", M_OUT),)
    if low in ("ls", "ls -l", "ls -la", "ls -al"):
        if shell.cwd == "~/logs":
            from missions import LS_LOGS
            return True, LS_LOGS
        from missions import LS_ROOT
        return True, LS_ROOT
    if low in ("cd logs", "cd ./logs"):
        shell.cwd = "~/logs"
        return True, ()
    if low in ("cd ..", "cd ~", "cd"):
        shell.cwd = "~"
        return True, ()
    if low == "history":
        rows = shell.editor.history[-10:]
        return True, tuple((f"{i + 1:4}  {cmd}", M_OUT) for i, cmd in enumerate(rows))
    if low == "whoami":
        return True, (("lug", M_OUT),)
    if low in ("date",):
        return True, (("Thu Nov 19 20:02:00 CST 2026", M_OUT),)
    if low in ("uname -a", "uname"):
        return True, (("Linux lug-booth 6.8.0-lug #1 SMP x86_64 GNU/Linux", M_OUT),)
    if low == "cat README.md":
        from missions import README
        return True, README
    if low == "cat notes.txt":
        return True, (("摊位备忘记：网线在左边抽屉。", M_OUT), ("下次记得带转接头。", M_DIM))
    if low == "cat logs/app.log":
        return True, (("2026-11-19 14:32:07 INFO  booth started", M_OUT),
                      ("2026-11-19 14:32:07 ERROR database connection lost", M_ERR),
                      ("2026-11-19 14:32:08 INFO  retrying in 3s", M_OUT))
    if low == "cat logs/error.log":
        return True, (("2026-11-19 14:32:09 ERROR retry limit reached", M_ERR),
                      ("2026-11-19 14:32:10 WARN  backing off", M_WARN))
    if low == "df -h":
        from missions import MISSIONS
        for m in MISSIONS:
            if m.title == "磁盘还有空间吗":
                return True, m.steps[0].output
    if low == "ps aux":
        return True, (("USER       PID %CPU %MEM    VSZ   RSS TTY STAT START   TIME COMMAND", M_DIM),
                      ("root         1  0.0  0.1 168000 12000 ?   Ss   19:58   0:01 /sbin/init", M_OUT),
                      ("lug       4242  0.4  1.2 128000 24000 pts/0 S+ 20:01   0:00 python3 booth.py", M_OUT))
    if low.startswith("echo "):
        return True, ((low[5:], M_OUT),)
    if low == "free -h":
        return True, (("               total        used        free      shared  buff/cache", M_DIM),
                      ("Mem:           7.7Gi       2.1Gi       4.8Gi       128Mi       0.8Gi", M_OUT))
    return False, ()


class Round:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.missions = pick_missions(self.rng, MISSION_COUNT)
        self.index = 0
        self.step = 0
        self.state = "playing"
        self.time_left = ROUND_TIME
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.mistakes = 0
        self.skips = 0
        self.step_time = 0.0
        self.hint_shown = False
        self.perfect = False
        self.rank = "D"
        self.finished_reason = ""

    @property
    def mission(self) -> Mission | None:
        if 0 <= self.index < len(self.missions):
            return self.missions[self.index]
        return None

    @property
    def current_step(self) -> Step | None:
        m = self.mission
        if m and self.step < len(m.steps):
            return m.steps[self.step]
        return None

    def multiplier(self) -> int:
        return min(4, 1 + self.combo // 3)

    def start(self, shell: Shell) -> None:
        shell.clear_log()
        shell.cwd = "~"
        shell.print("LUG 终端挑战 · SHELL QUEST", AMBER, bold=True)
        shell.print("75 秒 · 5 个任务 · 输入 hint 可以看提示", DIM)
        if self.mission:
            shell.mission_header(self.mission, 1, len(self.missions))
            shell.mission_step(self.mission, 1, len(self.mission.steps))

    def update(self, dt: float, shell: Shell) -> None:
        if self.state != "playing":
            return
        self.time_left -= dt
        self.step_time += dt
        if self.step_time > 12 and not self.hint_shown and self.mission:
            self.hint_shown = True
            shell.print(f"# 提示：{self.mission.hint}", AMBER)
        if self.time_left <= 0:
            self.time_left = 0
            self.finish(shell, "时间到")

    def _advance(self, shell: Shell, gain: int) -> None:
        m = self.mission
        if m is None:
            return
        self.step += 1
        self.step_time = 0
        self.hint_shown = False
        if self.step < len(m.steps):
            self.score += gain
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            shell.print(f"[ OK ] +{gain}", GREEN, bold=True)
            shell.mission_step(m, self.step + 1, len(m.steps))
            return

        # 当前任务完成
        bonus = m.points * self.multiplier()
        self.score += gain + bonus
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        shell.print(f"[ OK ] {m.title} +{bonus}", GREEN, bold=True)
        self.index += 1
        self.step = 0
        shell.cwd = "~"
        if self.index >= len(self.missions):
            self.finish(shell, "全部任务完成")
            return
        if self.mission:
            shell.mission_header(self.mission, self.index + 1, len(self.missions))
            shell.mission_step(self.mission, 1, len(self.mission.steps))

    def submit(self, line: str, shell: Shell) -> None:
        if self.state != "playing":
            return
        raw = line.strip()
        shell.echo(raw)
        if not raw:
            return
        line = " ".join(raw.split())
        if line == "clear":
            shell.clear_log()
            if self.mission:
                shell.mission_header(self.mission, self.index + 1, len(self.missions))
                shell.mission_step(self.mission, self.step + 1, len(self.mission.steps))
            return
        if line == "help":
            shell.print("# 可用命令：hint / skip / clear / pwd / ls / cat / cd", DIM)
            shell.print("# 行编辑：Tab 补全 · ↑↓ 历史 · Ctrl+←/→ 按词 · Ctrl+A/E 行首行尾", FAINT)
            return
        if line == "hint":
            if self.mission:
                self.hint_shown = True
                shell.print(f"# 提示：{self.mission.hint}", AMBER)
            return
        if line == "skip":
            self.time_left = max(0, self.time_left - 10)
            self.combo = 0
            self.skips += 1
            shell.print("[ SKIP ] -10s", RED, bold=True)
            self.index += 1
            self.step = 0
            self.step_time = 0.0
            self.hint_shown = False
            shell.cwd = "~"
            if self.index >= len(self.missions):
                self.finish(shell, "跳过")
            elif self.mission:
                shell.mission_header(self.mission, self.index + 1, len(self.missions))
                shell.mission_step(self.mission, 1, len(self.mission.steps))
            return

        step = self.current_step
        if step and step.match(line):
            shell.output(step.output)
            if step.cwd:
                shell.cwd = step.cwd
            gain = 40 * self.multiplier()
            self._advance(shell, gain)
            return

        ok, output = _generic(line, shell)
        if ok:
            shell.output(output)
            shell.print("# 命令能跑，但不是当前任务。", AMBER)
            return

        self.mistakes += 1
        self.combo = 0
        self.time_left = max(0.0, self.time_left - 2)
        cmd = line.split()[0]
        shell.print(f"bash: {cmd}: command not found", RED)
        shell.print("[ -2s ]", RED)

    def finish(self, shell: Shell, reason: str) -> None:
        if self.state != "playing":
            return
        self.state = "over"
        self.finished_reason = reason
        self.score += int(self.time_left) * 2
        completed = self.index >= len(self.missions)
        if completed and self.mistakes == 0 and self.skips == 0:
            self.perfect = True
            self.score += 200
        self.rank = rank_for(self.score)
        shell.print("")
        shell.print("[ SESSION END ]", AMBER, bold=True)
        shell.print(f"{reason} · score {self.score} · rank {self.rank}", WHITE, bold=True)
        shell.print(f"任务 {min(self.index, len(self.missions))}/{len(self.missions)} · "
                    f"最高连击 {self.max_combo} · 失误 {self.mistakes} · 跳过 {self.skips}", DIM)
        if self.perfect:
            shell.print("PERFECT +200", AMBER, bold=True)


def rank_for(score: int) -> str:
    if score >= 2200:
        return "S"
    if score >= 1600:
        return "A"
    if score >= 1000:
        return "B"
    if score >= 500:
        return "C"
    return "D"


LUG_ASCII = (
    (" _    _ _   _  ____", AMBER),
    ("| |  | | | | |/ ___|", AMBER),
    ("| |__| | |_| | |  _", TEAL),
    ("|  __  |  _  | |_| |", TEAL),
    ("|_|  |_|_| |_|\\____|", GREEN),
)


def _banner(shell: Shell) -> None:
    for line, color in LUG_ASCII:
        shell.print(line, color, bold=True)
    shell.print("")
    shell.print("LUG 终端挑战 · SHELL QUEST", AMBER, bold=True)
    shell.print("Linux User Group · 75 秒命令实战", DIM)


class Demo:
    """待机页：真实 shell 会话自动运行。"""

    def __init__(self, shell: Shell, seed: int | None = None):
        self.shell = shell
        self.rng = random.Random(seed)
        self.missions = pick_missions(self.rng, 5)
        self.gen = self._script()
        self.wait = 0.0
        self._tick()

    def _tick(self) -> None:
        try:
            self.wait = next(self.gen)
        except StopIteration:
            self.gen = self._script()
            self.wait = next(self.gen)

    def update(self, dt: float) -> None:
        self.wait -= dt
        while self.wait <= 0:
            self._tick()

    def _script(self):
        shell = self.shell
        shell.clear_log()
        shell.editor.clear()
        shell.cwd = "~"
        _banner(shell)
        shell.print("[ OK ] mounted /dev/booth", GREEN)
        shell.print("[ OK ] loaded mission pack", GREEN)
        shell.print("[ OK ] shell ready", GREEN)
        yield 1.2
        while True:
            for i, mission in enumerate(self.missions, 1):
                shell.mission_header(mission, i, len(self.missions))
                yield 0.7
                for step in mission.steps:
                    for ch in step.demo:
                        shell.editor.insert(ch)
                        yield 0.045
                    yield 0.25
                    shell.echo(shell.editor.buffer)
                    shell.editor.clear()
                    if step.cwd:
                        shell.cwd = step.cwd
                    shell.output(step.output)
                    yield 0.35
                shell.print(f"[ OK ] {mission.title}", GREEN, bold=True)
                shell.cwd = "~"
                yield 1.0
            yield 3.0
            shell.clear_log()
            _banner(shell)
            shell.print("[ OK ] shell ready", GREEN)
            yield 1.0
