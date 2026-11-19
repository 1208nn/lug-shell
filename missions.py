"""任务、模拟输出和命令补全词表。"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# 输出颜色名，由 shell/main 映射成具体 RGB
OK = "ok"
OUT = "out"
DIM = "dim"
ERR = "err"
WARN = "warn"
PATH = "path"


@dataclass(frozen=True)
class Step:
    accepts: tuple[str, ...]
    output: tuple[tuple[str, str], ...] = ()
    cwd: str | None = None
    demo: str = ""

    def match(self, line: str) -> bool:
        line = " ".join(line.strip().split())
        return any(re.fullmatch(p, line, re.IGNORECASE) for p in self.accepts)


@dataclass(frozen=True)
class Mission:
    title: str
    brief: str
    hint: str
    steps: tuple[Step, ...]
    level: int = 1
    points: int = 100


README = (
    ("LUG 摊位终端手册", OUT),
    ("", OUT),
    ("- 08:00 支摊，16:00 收摊", OUT),
    ("- 遇到问题先看日志", OUT),
    ("- TODO: 给 deploy.sh 加执行权限", WARN),
    ("- TODO: 把 logs 目录打包备份", WARN),
    ("", OUT),
    ("Linux User Group · 2026", DIM),
)

LS_ROOT = (
    ("total 32", DIM),
    ("drwxr-xr-x  5 lug lug 4096 Nov 19 20:02 .", OUT),
    ("drwxr-xr-x 12 lug lug 4096 Nov 19 19:58 ..", OUT),
    ("-rw-r--r--  1 lug lug  186 Nov 19 20:01 README.md", OUT),
    ("-rwxr-xr-x  1 lug lug  512 Nov 19 20:01 deploy.sh", OK),
    ("drwxr-xr-x  2 lug lug 4096 Nov 19 20:00 logs", PATH),
    ("-rw-r--r--  1 lug lug  120 Nov 19 20:01 notes.txt", OUT),
    ("-rw-r--r--  1 lug lug  420 Nov 19 20:01 app.log", OUT),
    ("-rw-r--r--  1 lug lug  508 Nov 19 20:01 error.log", ERR),
    ("-rw-r--r--  1 lug lug  982 Nov 19 20:01 access.log", OUT),
    ("drwxr-xr-x  8 lug lug 4096 Nov 19 19:59 .git", DIM),
)

LS_LOGS = (
    ("total 24", DIM),
    ("drwxr-xr-x 2 lug lug 4096 Nov 19 20:00 .", OUT),
    ("drwxr-xr-x 5 lug lug 4096 Nov 19 20:02 ..", OUT),
    ("-rw-r--r-- 1 lug lug  982 Nov 19 19:59 access.log", OUT),
    ("-rw-r--r-- 1 lug lug  744 Nov 19 19:59 app.log", OUT),
    ("-rw-r--r-- 1 lug lug  508 Nov 19 19:59 error.log", ERR),
)

MISSIONS: list[Mission] = [
    Mission(
        "目录侦察",
        "看看当前目录里都有什么，包括隐藏文件。",
        "ls -la",
        (Step((r"ls\s+-[a-z]*l[a-z]*a[a-z]*", r"ls\s+-[a-z]*a[a-z]*l[a-z]*",
               r"ls\s+-l\s+-a", r"ls\s+-a\s+-l"), LS_ROOT, demo="ls -la"),),
        1, 100,
    ),
    Mission(
        "读一下手册",
        "把摊位的 README.md 打开看看。",
        "cat README.md",
        (Step((r"(?:cat|bat|nl|less|more)\s+(?:\./)?README\.md",
               r"head\s+(?:-n\s+\d+\s+)?(?:\./)?README\.md",
               r"tail\s+(?:-n\s+\d+\s+)?(?:\./)?README\.md",
               r"sed\s+-n\s+.*README\.md"), README, demo="cat README.md"),),
        1, 100,
    ),
    Mission(
        "日志里的 ERROR",
        "logs 目录里藏着一条 ERROR，找出来。",
        "grep -r ERROR logs",
        (Step((r"(?:grep|rg|ack|ag)\s+-[a-z]*[rR]?[a-z]*\s+['\"]?ERROR['\"]?\s+\.?/?",
               r"(?:grep|rg|ack|ag)\s+-[a-z]*[rR][a-z]*\s+['\"]?ERROR['\"]?\s+logs/?",
               r"(?:grep|rg|ack|ag)\s+['\"]?ERROR['\"]?\s+\*\.log",
               r"(?:grep|rg|ack|ag)\s+['\"]?ERROR['\"]?\s+logs/?(?:(?:app|error)\.log)?",
               r"(?:grep|rg|ack|ag)\s+['\"]?ERROR['\"]?\s+\.?/?",
               r"rg\s+['\"]?ERROR['\"]?"),
              (("2026-11-19 14:32:07 ERROR database connection lost", ERR),
               ("2026-11-19 14:32:09 ERROR retry limit reached", ERR),
               ("2026-11-19 14:32:10 WARN  backing off", WARN)),
              demo="grep -r ERROR logs"),),
        1, 120,
    ),
    Mission(
        "把日志找出来",
        "列出当前目录下所有 .log 文件。",
        "ls *.log",
        (Step((r"(?:ls|eza|exa)(?:\s+-[a-zA-Z]+)*",
               r"(?:ls|eza|exa)(?:\s+-[a-zA-Z]+)*\s+(?:\./)?(?:logs/)?(?:app|error|access|\*)\.log",
               r"(?:ls|eza|exa)\s+-[a-zA-Z]*R[a-zA-Z]*",
               r"find\s+\.\s+.*-name\s+['\"]?\*\.log['\"]?",
               r"fd\s+.*\.log", r"fd\s+-e\s+log",
               r"rg\s+--files.*\.log['\"]?",
               r"rg\s+-g\s+['\"]?\*\.log['\"]?\s+--files",
               r"tree.*\.log"),
              (("access.log", PATH),
               ("app.log", PATH),
               ("error.log", PATH)),
              demo='ls *.log'),),
        1, 120,
    ),
    Mission(
        "磁盘还有空间吗",
        "用人类可读的方式看看磁盘占用。",
        "df -h",
        (Step((r"df\s+-h", r"df\s+-hT", r"df"),
              (("Filesystem      Size  Used Avail Use% Mounted on", DIM),
               ("/dev/sda1        40G   12G   26G  32% /", OUT),
               ("tmpfs           1.0G     0  1.0G   0% /dev/shm", OUT)),
              demo="df -h"),),
        1, 100,
    ),
    Mission(
        "谁在跑 Python",
        "找出正在运行的 Python 进程。",
        "ps aux | grep python",
        (Step((r"ps\s+(?:aux|\-ef)\s*\|\s*grep\s+python", r"pgrep\s+-a\s+python",
               r"ps\s+aux", r"ps\s+-ef"),
              (("lug  4242  0.4  1.2 128000 24000 pts/0  S+  20:01  0:00 python3 booth.py", OUT),),
              demo="ps aux | grep python"),),
        2, 150,
    ),
    Mission(
        "给脚本上权限",
        "deploy.sh 还没有执行权限，给它加上。",
        "chmod +x deploy.sh",
        (Step((r"chmod\s+\+x\s+deploy\.sh", r"chmod\s+[au]\+x\s+deploy\.sh",
               r"chmod\s+755\s+deploy\.sh"),
              (), demo="chmod +x deploy.sh"),),
        2, 150,
    ),
    Mission(
        "打包备份",
        "把 logs 目录打包成 logs.tar.gz。",
        "tar -czf logs.tar.gz logs",
        (Step((r"tar\s+-?c[a-z]*z[a-z]*f?\s+logs\.tar\.gz\s+logs/?",
               r"tar\s+czf\s+logs\.tar\.gz\s+logs/?",
               r"tar\s+-?c[a-z]*f\s+logs\.tar\.gz\s+logs/?"),
              (), demo="tar -czf logs.tar.gz logs"),),
        2, 160,
    ),
    Mission(
        "Git 状态",
        "看看当前仓库有没有未提交的改动。",
        "git status",
        (Step((r"git\s+status", r"git\s+status\s+-s"),
              (("On branch master", OUT),
               ("Changes not staged for commit:", WARN),
               ("  modified:   README.md", OUT),
               ("Untracked files:", WARN),
               ("  logs/", OUT),
               ("no changes added to commit", DIM)),
              demo="git status"),),
        2, 150,
    ),
    Mission(
        "看看响应头",
        "只请求 https://example.com 的响应头。",
        "curl -I https://example.com",
        (Step((r"curl\s+-[s]*I\s+https://example\.com/?",
               r"curl\s+-i\s+https://example\.com/?",
               r"curl\s+--head\s+https://example\.com/?"),
              (("HTTP/2 200", OK),
               ("content-type: text/html; charset=UTF-8", OUT),
               ("server: example", DIM),
               ("date: Thu, 19 Nov 2026 20:02:00 GMT", OUT)),
              demo="curl -I https://example.com"),),
        2, 160,
    ),
    Mission(
        "服务还活着吗",
        "查看 nginx 服务的状态。",
        "systemctl status nginx",
        (Step((r"systemctl\s+status\s+nginx(\.service)?",
               r"service\s+nginx\s+status"),
              (("● nginx.service - A high performance web server", OK),
               ("     Loaded: loaded (/lib/systemd/system/nginx.service; enabled)", OUT),
               ("     Active: active (running) since Thu 2026-11-19 19:58:00 CST", OK),
               ("   Main PID: 812 (nginx)", OUT)),
              demo="systemctl status nginx"),),
        2, 160,
    ),
    Mission(
        "进目录看错误",
        "先进入 logs，再看看 error.log 里写了什么。",
        "cd logs 然后 cat error.log",
        (Step((r"cd\s+logs/?",), cwd="~/logs", demo="cd logs"),
         Step((r"cat\s+\.?/?error\.log", r"tail\s+error\.log",
               r"less\s+error\.log"),
              (("2026-11-19 14:32:09 ERROR retry limit reached", ERR),
               ("2026-11-19 14:32:10 WARN  backing off", WARN),
               ("2026-11-19 14:32:14 INFO  service restarted", OK)),
              demo="cat error.log"),),
        2, 180,
    ),
    Mission(
        "找 TODO",
        "README.md 里还有几个 TODO，带行号找出来。",
        "grep -n TODO README.md",
        (Step((r"grep\s+-n\s+TODO\s+README\.md", r"grep\s+TODO\s+README\.md"),
              (("5:- TODO: 给 deploy.sh 加执行权限", WARN),
               ("6:- TODO: 把 logs 目录打包备份", WARN)),
              demo="grep -n TODO README.md"),),
        2, 150,
    ),
    Mission(
        "目录有多大",
        "看看当前目录下每个东西占多大。",
        "du -sh *",
        (Step((r"du\s+-sh\s+\*", r"du\s+-sh\s+\./\*", r"du\s+-sh\s+\."),
              (("4.0K    README.md", OUT),
               ("4.0K    deploy.sh", OUT),
               ("16K     logs", PATH),
               ("4.0K    notes.txt", OUT)),
              demo="du -sh *"),),
        2, 140,
    ),
    Mission(
        "结束进程",
        "PID 4242 的 Python 进程卡住了，结束它。",
        "kill 4242",
        (Step((r"kill\s+4242", r"kill\s+-9\s+4242", r"kill\s+-TERM\s+4242"),
              (), demo="kill 4242"),),
        3, 180,
    ),
]

def pick_missions(rng: random.Random, n: int = 5) -> list[Mission]:
    by_level: dict[int, list[Mission]] = {}
    for m in MISSIONS:
        by_level.setdefault(m.level, []).append(m)
    picked: list[Mission] = []
    plan = [1, 1, 2, 2, 3]
    for level in plan[:n]:
        pool = by_level.get(level, [])
        if not pool:
            pool = [m for m in MISSIONS if m not in picked]
        if pool:
            choice = rng.choice(pool)
            picked.append(choice)
            for bucket in by_level.values():
                if choice in bucket:
                    bucket.remove(choice)
    rng.shuffle(picked)
    return picked[:n]


COMPLETION_WORDS = {
    "ls", "ls -l", "ls -la", "cd", "cd logs", "cd ..", "pwd", "cat",
    "cat README.md", "cat notes.txt", "cat logs/app.log", "cat logs/error.log",
    "grep", "grep -r ERROR logs", "grep -n TODO README.md",
    "find", "find . -name", "df", "df -h", "du", "du -sh", "ps", "ps aux",
    "ps aux | grep python", "chmod", "chmod +x", "chmod +x deploy.sh",
    "tar", "tar -czf", "tar -xzf", "git", "git status", "git add", "git commit",
    "curl", "curl -I", "curl -I https://example.com", "systemctl",
    "systemctl status", "systemctl status nginx", "journalctl", "kill",
    "kill 4242", "make", "make clean", "ssh", "scp", "rsync", "docker",
    "docker ps", "docker ps -a", "top", "free", "free -h", "whoami",
    "date", "uname", "uname -a", "history", "clear", "help", "hint", "skip",
    "README.md", "deploy.sh", "notes.txt", "logs", "logs/app.log",
    "logs/error.log", "logs/access.log", "logs.tar.gz", "example.com",
}


def completion_words() -> set[str]:
    words: set[str] = set()
    for item in COMPLETION_WORDS:
        words.update(item.split())
    for m in MISSIONS:
        for step in m.steps:
            words.update(step.demo.split())
    words.update({"README.md", "deploy.sh", "notes.txt", "logs", "app.log",
                  "error.log", "access.log", "logs.tar.gz", "example.com"})
    return words
