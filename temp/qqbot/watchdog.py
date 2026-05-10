#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QQ Bot 看门狗 v1.0
- 每10秒轮询bot进程(PID或pythonw.exe中的bot.py)
- 进程消失→自动重启(调用start_hidden.vbs)
- 日志7天轮转：qqbot/logs/watchdog.log
- 启动方式: python watchdog.py [--daemon]
"""

import os, sys, time, subprocess
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
LOG_DIR = BASE / "logs"
LOG_FILE = LOG_DIR / "watchdog.log"
BOT_PY = BASE / "bot.py"
VBS = BASE / "start_hidden.vbs"
CHECK_INTERVAL = 10  # seconds
LOG_RETENTION_DAYS = 7
MAX_LOG_SIZE = 200 * 1024  # 200KB per log file

def log(msg: str):
    """写日志，自动处理7天轮转"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"

    # 轮转：超过7天或超过200KB则重命名
    if LOG_FILE.exists():
        age = datetime.now() - datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        if age > timedelta(days=LOG_RETENTION_DAYS) or LOG_FILE.stat().st_size > MAX_LOG_SIZE:
            backup = LOG_DIR / f"watchdog.{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            LOG_FILE.rename(backup)
            # 清理超过7天的旧日志
            for f in LOG_DIR.glob("watchdog.*.log"):
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days > LOG_RETENTION_DAYS:
                    f.unlink()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    # NOTE: no print() - pythonw.exe has no stdout

def find_bot_pids() -> list:
    """查找所有bot.py的pythonw.exe进程PID (PowerShell方案，稳定可靠)"""
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process -Filter "name=\'pythonw.exe\'" | '
            'Where-Object {$_.CommandLine -like \'*bot.py*\'} | '
            'Select-Object -ExpandProperty ProcessId'
        )
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        pids = []
        for line in r.stdout.strip().split('\n'):
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        return pids
    except Exception as e:
        log(f"WARN 查找bot进程失败: {e}")
        return []

def restart_bot():
    """通过VBS脚本重新启动Bot"""
    if not VBS.exists():
        log("ERROR start_hidden.vbs 丢失，尝试直接启动")
        subprocess.Popen(
            [sys.executable, str(BOT_PY)],
            cwd=str(BASE),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return

    subprocess.Popen(
        ['wscript', str(VBS)],
        cwd=str(BASE),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )
    log("ACTION 已触发Bot重启 (wscript start_hidden.vbs)")

def run():
    log("START QQ Bot看门狗启动，监控间隔=10s，日志保留=7天")
    first_run = True
    consecutive_failures = 0
    cycle_count = 0
    HEARTBEAT_INTERVAL = 6  # 每6轮(~60s)写一次心跳

    while True:
        try:
            cycle_count += 1
            pids = find_bot_pids()

            if pids:
                if first_run:
                    log(f"OK Bot进程在线: PIDs={pids}")
                    first_run = False
                elif cycle_count % HEARTBEAT_INTERVAL == 0:
                    log(f"BEAT 轮次#{cycle_count} 进程在线: {len(pids)}个Bot")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                log(f"ALERT Bot进程全部消失! (连续{consecutive_failures}次)")
                restart_bot()
                # 等待启动完成
                time.sleep(5)
                new_pids = find_bot_pids()
                if new_pids:
                    log(f"OK 重启成功: 新PIDs={new_pids}")
                    consecutive_failures = 0
                else:
                    log(f"ERROR 重启后仍未检测到Bot进程")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log("STOP 看门狗收到中断信号，退出")
            break
        except Exception as e:
            log(f"ERROR 看门狗异常: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run()