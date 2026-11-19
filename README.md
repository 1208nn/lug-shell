# LUG 终端挑战

摆在 LUG 摊位上的 **75 秒 shell 任务游戏**。

不是命令雨，也不是点来点去的假终端。玩家面对的是一台正在运行的 Linux 机器：左边是真实的 shell 提示符，任务以注释出现在终端里，玩家用真实的命令、Tab 补全和行编辑快捷键完成任务。

```text
 LUG 终端挑战                     MISSION 2/5   TIME 61   SCORE 0280   COMBO x2
──────────────────────────────────────────────────────────────────────────────
 # 任务 2/5 · 日志里的 ERROR
 # logs 目录里藏着一条 ERROR，找出来。
 # 输入 hint 看提示 · skip 跳过（-10s）
 lug@booth:~$ grep -r ERROR logs
 logs/app.log: 2026-11-19 14:32:07 ERROR  database connection lost
 logs/error.log: 2026-11-19 14:32:09 ERROR  retry limit reached
 [ OK ] +80

 # 任务 3/5 · Git 状态
 # 看看当前仓库有没有未提交的改动。
 lug@booth:~$ git status
 On branch master
 Changes not staged for commit:
   modified:   README.md
──────────────────────────────────────────────────────────────────────────────
 lug@booth:~$ _
 Tab 补全 · ↑↓ 历史 · Ctrl+←/→ 按词 · Ctrl+W 删词          Ctrl-Q 退出
```

## 运行

需要 [uv](https://docs.astral.sh/uv/)。`mise.toml` 只负责提供 `uv`。

```bash
cd lug-shell
./lug
```

或者：

```bash
mise exec -- uv run python main.py
```

终端至少 **80 x 24**，推荐全屏 + 真彩。窗口太小时会提示，放大后自动继续。

## 怎么玩

- 待机时是一段真实 shell 会话在自动运行；按任意键开始。
- 75 秒内完成 5 个任务。
- 任务说明以 `#` 注释出现在终端里，大多数任务一条命令就能完成。
- 执行正确命令后会打印模拟输出，进入下一任务。
- 卡住可以输入 `hint` 看提示，或输入 `skip` 跳过（扣 10 秒）。
- 时间结束或 5 个任务完成，进入结算。

### 行编辑

这里按真实 shell 的习惯来：

| 键 | 作用 |
| --- | --- |
| ← / → | 移动光标 |
| Ctrl+← / Ctrl+→ | 按单词移动 |
| Home / End、Ctrl+A / Ctrl+E | 行首 / 行尾 |
| Ctrl+W | 删除前一个单词 |
| Ctrl+U / Ctrl+K | 删除到行首 / 行尾 |
| Backspace / Delete | 删除字符 |
| ↑ / ↓ | 命令历史 |
| Tab | 按单词补全；多个候选会列出来 |
| Enter | 执行 |
| Ctrl+C | 清空当前输入行 |
| Ctrl+L | 清屏并重新显示当前任务 |
| Esc | 放弃本局，回待机 |
| Ctrl+Q | 退出 |

## 任务

任务来自一个模拟的摊位机器：

- 目录侦察：`ls -la`
- 读手册：`cat README.md`
- 找日志：`grep -r ERROR logs`
- 找文件：`find . -name "*.log"`
- 磁盘：`df -h`
- 进程：`ps aux | grep python`
- 权限：`chmod +x deploy.sh`
- 打包：`tar -czf logs.tar.gz logs`
- Git：`git status`
- 网络：`curl -I https://example.com`
- 服务：`systemctl status nginx`
- 两步任务：`cd logs` 然后 `cat error.log`
- 还有 `du -sh *`、`grep -n TODO README.md`、`kill 4242`

每条任务都带中文说明和提示，既是大字报也是命令小抄。

## 计分

- 每完成一步有基础分，连击提升倍率（最高 x4）。
- 完成整个任务有额外奖励。
- 失误会断连击并扣 2 秒；`skip` 扣 10 秒。
- 剩余时间按 2 分/秒折算。
- 5 个任务全清且零失误、零跳过：`PERFECT +200`。
- 评级：S ≥ 2200，A ≥ 1600，B ≥ 1000，C ≥ 500，其余 D。

## 摊位模式

- 待机页自动运行一段 shell 会话，路人能直接看懂“输入命令 → 输出结果”的节奏。
- 结算页停留 25 秒，排行榜停留 15 秒，自动回待机。
- 排行榜保存在本地：

```text
~/.local/share/lug-shell/scores.json
```

也可以用 `LUG_SHELL_SCORES` 指定路径。清空：

```bash
./lug --reset-scores
```

## 技术

- Python 3.13 + `uv`，零第三方依赖。
- 真彩 ANSI 画布，按行 diff 输出。
- 不依赖图片协议，只需要一个能显示真彩字符的终端。
- 行编辑器、历史、补全、任务校验全部在本地完成，不联网。
- 所有命令只做字符串校验和模拟输出，**不会真的执行**；摊位机器是安全的。

## 项目结构

```text
lug            启动脚本
main.py        状态机、HUD、待机/回合/结算
shell.py       行编辑器、终端滚动区、任务回合、待机脚本
missions.py    任务、模拟输出、补全词表
canvas.py      真彩画布、宽字符、cursor
term.py        raw 输入、终端尺寸、快捷键解析
scores.py      本地排行榜
```

## 开发

```bash
mise exec -- uv run python -m py_compile main.py shell.py missions.py canvas.py term.py scores.py
```

固定随机种子：

```bash
./lug --seed 7
```

`~/lug-rain` 是之前的命令雨原型，保留作对照；这一版是重新按“真实 shell 使用感”做的。
