#!/usr/bin/env python3
"""LUG 终端挑战 —— 摊位上的 shell 任务游戏。"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time

import scores
from canvas import (
    AMBER, BG, DIM, FAINT, GREEN, INK, PINK, RED, TEAL, WHITE,
    Canvas,
)
from missions import completion_words
from shell import Demo, Editor, Round, Shell
from term import Terminal

MIN_W, MIN_H = 80, 24
FPS = 30
WORDS = completion_words()


def draw_hud(c: Canvas, w: int, state: str, rnd: Round | None, board: list[dict],
             now: float) -> None:
    c.fill(0, 0, w, 1, " ", INK, BG)
    c.put(0, 0, " LUG 终端挑战 ", BG, AMBER, bold=True)
    if state == "attract":
        top = board[0] if board else None
        if top:
            text = f"TOP 1  {top.get('name', '???')}  {int(top.get('score', 0))}"
        else:
            text = "TOP 1  ---"
        c.center(0, text, AMBER if top else FAINT, BG, bold=bool(top))
        c.right(w - 6, 0, "SYS.OK", TEAL, BG, bold=True)
        c.put(w - 1, 0, "|/-\\"[int(now * 8) % 4], AMBER, BG, bold=True)
    else:
        if state == "playing" and rnd:
            c.center(0, f"MISSION {min(rnd.index + 1, len(rnd.missions))}/{len(rnd.missions)}",
                     WHITE, BG, bold=True)
            t = max(0, int(math.ceil(rnd.time_left)))
            color = RED if t <= 10 else AMBER if t <= 25 else TEAL
            c.right(w - 1, 0,
                    f"TIME {t:02d}   SCORE {rnd.score:04d}   COMBO x{rnd.multiplier()}",
                    color, BG, bold=True)
        elif state in ("initials", "over_wait") and rnd:
            c.center(0, f"SESSION END · RANK {rnd.rank}", PINK, BG, bold=True)
            c.right(w - 1, 0, f"SCORE {rnd.score:04d}", AMBER, BG, bold=True)
        elif state == "board" and rnd:
            c.center(0, "LEADERBOARD", AMBER, BG, bold=True)
            c.right(w - 1, 0, f"SCORE {rnd.score:04d}", TEAL, BG, bold=True)
    c.hline(0, 1, w, "─", FAINT, BG)


def draw_footer(c: Canvas, w: int, h: int, state: str, now: float) -> None:
    if state == "attract":
        label = "按任意键开始"
        color = WHITE if int(now * 2) % 2 == 0 else AMBER
        c.put(1, h - 1, label, color, BG, bold=True)
        c.right(w - 1, h - 1, "Ctrl-Q 退出", FAINT, BG)
    elif state == "playing":
        c.put(1, h - 1, "Tab 补全 · ↑↓ 历史 · Ctrl+←/→ 按词 · Ctrl+W 删词",
              FAINT, BG)
        c.right(w - 1, h - 1, "Ctrl-Q 退出", FAINT, BG)
    elif state == "initials":
        c.put(1, h - 1, "A-Z 0-9 · Enter 确认 · Backspace 删除", FAINT, BG)
        c.right(w - 1, h - 1, "Ctrl-Q 退出", FAINT, BG)
    else:
        c.put(1, h - 1, "按任意键回到待机", DIM, BG)
        c.right(w - 1, h - 1, "Ctrl-Q 退出", FAINT, BG)


def draw_too_small(c: Canvas, w: int, h: int) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    c.center(max(0, h // 2 - 2), "终端太小了", AMBER, BG, bold=True)
    c.center(max(0, h // 2), f"至少需要 {MIN_W} x {MIN_H}", DIM, BG)
    c.center(max(0, h // 2 + 1), f"当前 {w} x {h}", FAINT, BG)


def leaderboard_lines(board: list[dict], highlight_name: str = "",
                      highlight_score: int = -1) -> list[tuple[str, str, bool]]:
    out: list[tuple[str, str, bool]] = [("", INK, False), ("[ LEADERBOARD ]", AMBER, True)]
    if not board:
        out.append(("  还没有记录", FAINT, False))
        return out
    for i, row in enumerate(board[:8], 1):
        name = str(row.get("name", "???"))[:3]
        score = int(row.get("score", 0))
        combo = int(row.get("combo", 0))
        hot = name == highlight_name and score == highlight_score
        color = AMBER if hot else INK if i <= 3 else DIM
        out.append((f"  {i:>2}. {name}   {score:>6}   最高连击 {combo}", color, hot))
    return out


def handle_editor_key(key: str, editor: Editor, shell: Shell, initials: bool = False) -> str | None:
    """返回 'submit' / 'quit' / None。"""
    if key == "ctrl-q":
        return "quit"
    if key == "ctrl-c":
        editor.clear()
    elif key == "backspace":
        editor.backspace()
    elif key == "delete":
        editor.delete()
    elif key in ("left", "ctrl-b"):
        editor.left()
    elif key in ("right", "ctrl-f"):
        editor.right()
    elif key in ("home", "ctrl-a"):
        editor.home()
    elif key in ("end", "ctrl-e"):
        editor.end()
    elif key in ("ctrl-left", "ctrl-b", "alt-b"):
        editor.word_left()
    elif key in ("ctrl-right", "ctrl-f", "alt-f"):
        editor.word_right()
    elif key == "ctrl-w":
        editor.kill_word()
    elif key == "ctrl-u":
        editor.kill_start()
    elif key == "ctrl-k":
        editor.kill_end()
    elif key in ("up", "ctrl-p"):
        editor.up()
    elif key in ("down", "ctrl-n"):
        editor.down()
    elif key == "ctrl-l":
        shell.clear_log()
    elif key == "tab":
        cands = editor.complete(WORDS)
        if len(cands) > 1:
            line = "# 补全: " + "  ".join(cands[:10])
            if len(cands) > 10:
                line += " …"
            shell.print(line, FAINT)
    elif key == "enter":
        return "submit"
    elif len(key) == 1 and key.isprintable():
        if initials:
            if key.isalnum() and len(editor.buffer) < 3:
                editor.insert(key.upper())
        else:
            editor.insert(key)
    return None


def print_board(shell: Shell, board: list[dict], name: str, score: int) -> None:
    for text, color, bold in leaderboard_lines(board, name, score):
        shell.print(text, color, bold)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lug-shell", description="LUG 终端挑战 —— shell 任务游戏")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--reset-scores", action="store_true")
    args = ap.parse_args(argv or sys.argv[1:])

    if args.reset_scores:
        print(f"已清空 {scores.reset()}")
        return 0

    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    board = scores.load()
    try:
        term = Terminal()
    except Exception as e:
        print(f"启动失败：{e}", file=sys.stderr)
        return 1

    shell = Shell()
    demo: Demo | None = Demo(shell, seed)
    rnd: Round | None = None
    name_editor: Editor | None = None
    state = "attract"
    board_timer = 0.0
    over_timer = 0.0
    last_size = None
    prev_rows = None
    last = time.monotonic()
    running = True

    with term:
        while running:
            frame_start = time.monotonic()
            now = frame_start
            dt = min(0.25, frame_start - last)
            last = frame_start
            w, h = term.size()
            if (w, h) != last_size:
                last_size = (w, h)
                prev_rows = None
                term.clear()

            keys = term.read_keys(0.0)
            if not keys:
                keys = term.read_keys(0.002)

            if w < MIN_W or h < MIN_H:
                frame = Canvas(w, h)
                draw_too_small(frame, w, h)
                text, prev_rows = frame.render(prev_rows)
                term.write(text)
                term.flush()
                for key in keys:
                    if key == "ctrl-q":
                        running = False
                time.sleep(1 / FPS)
                last = time.monotonic()
                continue

            if state == "attract":
                if demo:
                    demo.update(dt)
                for key in keys:
                    if key == "ctrl-q":
                        running = False
                        break
                    if key == "ctrl-c":
                        continue
                    shell = Shell()
                    rnd = Round(rng.randrange(1_000_000))
                    rnd.start(shell)
                    state = "playing"
                    demo = None
                    name_editor = None
                    prev_rows = None
                    term.clear()
                    break

            elif state == "playing" and rnd:
                rnd.update(dt, shell)
                for key in keys:
                    if key == "esc":
                        state = "attract"
                        shell = Shell()
                        demo = Demo(shell, rng.randrange(1_000_000))
                        rnd = None
                        prev_rows = None
                        term.clear()
                        break
                    if key == "ctrl-l":
                        shell.clear_log()
                        if rnd.mission:
                            shell.mission_header(rnd.mission, rnd.index + 1, len(rnd.missions))
                            shell.mission_step(rnd.mission, rnd.step + 1, len(rnd.mission.steps))
                        continue
                    action = handle_editor_key(key, shell.editor, shell)
                    if action == "quit":
                        running = False
                        break
                    if action == "submit":
                        line = shell.editor.submit()
                        rnd.submit(line, shell)
                        if rnd.state != "playing":
                            break
                if rnd and rnd.state != "playing" and state == "playing":
                    if scores.qualifies(rnd.score):
                        shell.print("")
                        shell.print("输入 3 个字母上榜，Enter 确认。", AMBER, bold=True)
                        name_editor = Editor()
                        state = "initials"
                        over_timer = 0.0
                    else:
                        state = "over_wait"
                        over_timer = 0.0

            elif state == "initials" and rnd and name_editor:
                over_timer += dt
                for key in keys:
                    if key == "esc":
                        state = "attract"
                        shell = Shell()
                        demo = Demo(shell, rng.randrange(1_000_000))
                        rnd = None
                        prev_rows = None
                        term.clear()
                        break
                    action = handle_editor_key(key, name_editor, shell, initials=True)
                    if action == "quit":
                        running = False
                        break
                    if action == "submit":
                        name = (name_editor.buffer or "YOU").upper()[:3]
                        board = scores.save(name, rnd.score, rnd.max_combo)
                        shell.print("")
                        shell.print(f"[ OK ] {name} 记入排行榜", GREEN, bold=True)
                        print_board(shell, board, name, rnd.score)
                        state = "board"
                        board_timer = 0.0
                        break
                if over_timer > 25 and state == "initials":
                    state = "attract"
                    shell = Shell()
                    demo = Demo(shell, rng.randrange(1_000_000))
                    rnd = None
                    prev_rows = None
                    term.clear()

            elif state == "over_wait" and rnd:
                over_timer += dt
                for key in keys:
                    if key == "ctrl-q":
                        running = False
                        break
                    state = "attract"
                    shell = Shell()
                    demo = Demo(shell, rng.randrange(1_000_000))
                    rnd = None
                    prev_rows = None
                    term.clear()
                    break
                if over_timer > 15 and state == "over_wait":
                    state = "attract"
                    shell = Shell()
                    demo = Demo(shell, rng.randrange(1_000_000))
                    rnd = None
                    prev_rows = None
                    term.clear()

            elif state == "board" and rnd:
                board_timer += dt
                for key in keys:
                    if key == "ctrl-q":
                        running = False
                        break
                    state = "attract"
                    shell = Shell()
                    demo = Demo(shell, rng.randrange(1_000_000))
                    rnd = None
                    prev_rows = None
                    term.clear()
                    break
                if board_timer > 15 and state == "board":
                    state = "attract"
                    shell = Shell()
                    demo = Demo(shell, rng.randrange(1_000_000))
                    rnd = None
                    prev_rows = None
                    term.clear()

            if not running:
                break

            frame = Canvas(w, h)
            draw_hud(frame, w, state, rnd, board, now)
            draw_footer(frame, w, h, state, now)
            if state == "initials" and name_editor:
                shell.render(frame, w, h, "initials> ", show_cursor=int(now * 2) % 2 == 0,
                             input_color=AMBER)
            elif state in ("playing", "attract"):
                shell.render(frame, w, h, shell.prompt(), show_cursor=int(now * 2) % 2 == 0)
            else:
                shell.render(frame, w, h, shell.prompt(), show_cursor=False)
            text, prev_rows = frame.render(prev_rows)
            term.write(text)
            term.flush()

            spent = time.monotonic() - frame_start
            if spent < 1 / FPS:
                time.sleep(1 / FPS - spent)

    print("收摊了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
