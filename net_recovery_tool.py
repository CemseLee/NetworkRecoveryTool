# -*- coding: utf-8 -*-
"""
网络恢复工具 - Network Recovery Tool
一键执行 Windows 网络重置命令（需管理员权限）
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import sys
import os
import ctypes
import winreg
import time


# ======== 检测管理员权限 ========
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def check_and_relaunch():
    """如果不是管理员，请求提权后重启"""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1
        )
        sys.exit()


# ======== 命令定义 ========
COMMANDS = [
    {
        "id": "winsock",
        "label": "netsh winsock reset",
        "description": "重置 Winsock 目录 — 修复套接字连接问题",
        "cmd": "netsh winsock reset",
        "needs_reboot": True,
    },
    {
        "id": "ip_reset",
        "label": "netsh int ip reset",
        "description": "重置 TCP/IP 协议栈 — 修复 IP 配置问题",
        "cmd": "netsh int ip reset",
        "needs_reboot": True,
    },
    {
        "id": "release",
        "label": "ipconfig /release",
        "description": "释放当前 IP 地址 — 断开 DHCP 租约",
        "cmd": "ipconfig /release",
        "needs_reboot": False,
    },
    {
        "id": "renew",
        "label": "ipconfig /renew",
        "description": "重新获取 IP 地址 — 向 DHCP 申请新 IP",
        "cmd": "ipconfig /renew",
        "needs_reboot": False,
    },
    {
        "id": "flushdns",
        "label": "ipconfig /flushdns",
        "description": "刷新 DNS 缓存 — 清除过期的 DNS 解析记录",
        "cmd": "ipconfig /flushdns",
        "needs_reboot": False,
    },
]

ORDERED_IDS = ["flushdns", "release", "renew", "winsock", "ip_reset"]
"""推荐执行顺序：先清 DNS → 释放 IP → 续租 IP → 重置 Winsock → 重置 TCP/IP"""


# ======== 主应用 ========
class NetRecoveryTool:
    FONT_FAMILY = "Microsoft YaHei UI"
    BG_COLOR = "#f0f2f5"
    CARD_BG = "#ffffff"
    ACCENT = "#0078d4"
    ACCENT_HOVER = "#106ebe"
    SUCCESS = "#107c10"
    ERROR = "#d13438"
    WARNING = "#ff8c00"
    TEXT_PRIMARY = "#1a1a1a"
    TEXT_SECONDARY = "#666666"

    def __init__(self, root):
        self.root = root
        self.root.title("网络恢复工具 Network Recovery Tool")
        self.root.geometry("780x680")
        self.root.minsize(680, 580)
        self.root.configure(bg=self.BG_COLOR)

        # 设置图标（如果有）
        try:
            self.root.iconbitmap(default="")
        except:
            pass

        # 变量
        self.check_vars = {}
        self.is_running = False
        self.output_lines = []

        # 构建 UI
        self._setup_styles()
        self._build_header()
        self._build_command_list()
        self._build_action_bar()
        self._build_output()
        self._build_status_bar()

        # 默认全选
        for var in self.check_vars.values():
            var.set(True)

        # 绑定键盘事件
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<Escape>", lambda e: self.root.focus())

        self._log("🔧 网络恢复工具已启动")
        if not is_admin():
            self._log("⚠️  当前未以管理员身份运行，部分命令可能执行失败！", "warning")
            self._log("💡 建议点击「以管理员运行」按钮重新启动", "info")
        else:
            self._log("✅ 已获取管理员权限，可以执行所有命令", "success")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Tool.TButton", font=(self.FONT_FAMILY, 10), padding=(12, 6))
        style.configure("Accent.TButton", font=(self.FONT_FAMILY, 10, "bold"), padding=(14, 8))
        style.configure("Status.TLabel", font=(self.FONT_FAMILY, 9), foreground=self.TEXT_SECONDARY)

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.BG_COLOR, padx=24)
        header.pack(fill="x", pady=(20, 8))

        title = tk.Label(
            header,
            text="🛜  网络恢复工具",
            font=(self.FONT_FAMILY, 20, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_COLOR,
            anchor="w",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="一键执行 Windows 网络重置命令，修复网络连接问题",
            font=(self.FONT_FAMILY, 10),
            fg=self.TEXT_SECONDARY,
            bg=self.BG_COLOR,
            anchor="w",
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # 管理员状态指示
        admin_frame = tk.Frame(header, bg=self.BG_COLOR)
        admin_frame.pack(anchor="w", pady=(6, 0))

        if is_admin():
            admin_badge = tk.Label(
                admin_frame,
                text="✅ 管理员权限已获取",
                font=(self.FONT_FAMILY, 9, "bold"),
                fg=self.SUCCESS,
                bg="#e6f4ea",
                padx=10,
                pady=2,
            )
        else:
            admin_badge = tk.Label(
                admin_frame,
                text="⚠️  当前未以管理员权限运行",
                font=(self.FONT_FAMILY, 9, "bold"),
                fg=self.ERROR,
                bg="#fce8e6",
                padx=10,
                pady=2,
            )
        admin_badge.pack(side="left")
        admin_badge.configure(relief="flat", bd=0)

    def _build_command_list(self):
        container = tk.Frame(self.root, bg=self.BG_COLOR, padx=24)
        container.pack(fill="x", pady=(12, 4))

        # 分区标题
        section_label = tk.Label(
            container,
            text="选择要执行的命令",
            font=(self.FONT_FAMILY, 12, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_COLOR,
            anchor="w",
        )
        section_label.pack(anchor="w")

        # 卡片容器
        card = tk.Frame(container, bg=self.CARD_BG, bd=0, highlightthickness=0)
        card.pack(fill="x", pady=(8, 0))
        # 圆角效果通过 padx + relief 模拟
        for child in (
            tk.Frame(card, bg=self.CARD_BG, padx=16, pady=4),
            tk.Frame(card, bg=self.CARD_BG, padx=16, pady=4),
            tk.Frame(card, bg=self.CARD_BG, padx=16, pady=4),
            tk.Frame(card, bg=self.CARD_BG, padx=16, pady=4),
            tk.Frame(card, bg=self.CARD_BG, padx=16, pady=4),
        ):
            child.pack(fill="x")

        # 按推荐顺序排列命令
        for idx, cmd_id in enumerate(ORDERED_IDS):
            cmd = next(c for c in COMMANDS if c["id"] == cmd_id)
            row = tk.Frame(card, bg=self.CARD_BG, padx=16, pady=6)
            row.pack(fill="x")

            # 序号
            num_label = tk.Label(
                row,
                text=f"0{idx + 1}",
                font=(self.FONT_FAMILY, 10, "bold"),
                fg=self.ACCENT,
                bg=self.CARD_BG,
                width=3,
                anchor="e",
            )
            num_label.pack(side="left", padx=(0, 12))

            # Checkbox
            var = tk.BooleanVar()
            self.check_vars[cmd_id] = var
            cb = tk.Checkbutton(
                row,
                text="",
                variable=var,
                bg=self.CARD_BG,
                activebackground=self.CARD_BG,
                highlightthickness=0,
                bd=0,
            )
            cb.pack(side="left")

            # 命令标签
            cmd_label = tk.Label(
                row,
                text=cmd["label"],
                font=(self.FONT_FAMILY, 11, "bold"),
                fg=self.TEXT_PRIMARY,
                bg=self.CARD_BG,
                anchor="w",
            )
            cmd_label.pack(side="left", padx=(4, 8))

            # 需要重启标签
            if cmd["needs_reboot"]:
                reboot_badge = tk.Label(
                    row,
                    text="需重启",
                    font=(self.FONT_FAMILY, 8),
                    fg=self.WARNING,
                    bg="#fff4e5",
                    padx=6,
                    pady=1,
                )
                reboot_badge.pack(side="left")

            # 描述（靠右）
            desc_label = tk.Label(
                row,
                text=cmd["description"],
                font=(self.FONT_FAMILY, 9),
                fg=self.TEXT_SECONDARY,
                bg=self.CARD_BG,
                anchor="w",
            )
            desc_label.pack(side="right")

            # 分隔线
            if idx < len(ORDERED_IDS) - 1:
                sep = tk.Frame(row, height=1, bg="#e8e8e8", bd=0)
                sep.pack(fill="x", pady=(6, 0))

    def _build_action_bar(self):
        bar = tk.Frame(self.root, bg=self.BG_COLOR, padx=24)
        bar.pack(fill="x", pady=(10, 4))

        # 左侧 - 选择按钮
        select_frame = tk.Frame(bar, bg=self.BG_COLOR)
        select_frame.pack(side="left")

        self.btn_select_all = tk.Button(
            select_frame,
            text="☑ 全选",
            font=(self.FONT_FAMILY, 9),
            bg=self.CARD_BG,
            fg=self.TEXT_PRIMARY,
            bd=1,
            relief="solid",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self.select_all,
        )
        self.btn_select_all.pack(side="left", padx=(0, 6))

        self.btn_deselect_all = tk.Button(
            select_frame,
            text="☐ 取消全选",
            font=(self.FONT_FAMILY, 9),
            bg=self.CARD_BG,
            fg=self.TEXT_PRIMARY,
            bd=1,
            relief="solid",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self.deselect_all,
        )
        self.btn_deselect_all.pack(side="left")

        # 右侧 - 操作按钮
        action_frame = tk.Frame(bar, bg=self.BG_COLOR)
        action_frame.pack(side="right")

        self.btn_run_admin = tk.Button(
            action_frame,
            text="🔐  以管理员运行",
            font=(self.FONT_FAMILY, 9),
            bg="#fff4e5",
            fg=self.WARNING,
            bd=1,
            relief="solid",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self.relaunch_as_admin,
        )
        self.btn_run_admin.pack(side="right", padx=(6, 0))

        self.btn_execute = tk.Button(
            action_frame,
            text="▶  执行选中命令",
            font=(self.FONT_FAMILY, 11, "bold"),
            bg=self.ACCENT,
            fg="white",
            bd=0,
            padx=22,
            pady=6,
            cursor="hand2",
            command=self.execute_selected,
        )
        self.btn_execute.pack(side="right")

    def _build_output(self):
        container = tk.Frame(self.root, bg=self.BG_COLOR, padx=24)
        container.pack(fill="both", expand=True, pady=(6, 8))

        section_label = tk.Label(
            container,
            text="执行输出",
            font=(self.FONT_FAMILY, 11, "bold"),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_COLOR,
            anchor="w",
        )
        section_label.pack(anchor="w")

        self.output_text = scrolledtext.ScrolledText(
            container,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            bd=0,
            padx=12,
            pady=10,
            wrap="word",
            height=12,
            state="disabled",
        )
        self.output_text.pack(fill="both", expand=True, pady=(6, 0))

        # 配置 tag
        self.output_text.tag_configure("default", foreground="#d4d4d4")
        self.output_text.tag_configure("success", foreground="#4ec9b0")
        self.output_text.tag_configure("error", foreground="#f44747")
        self.output_text.tag_configure("warning", foreground="#dcdcaa")
        self.output_text.tag_configure("info", foreground="#569cd6")
        self.output_text.tag_configure("header", foreground="#c586c0", font=("Consolas", 10, "bold"))
        self.output_text.tag_configure("cmd", foreground="#9cdcfe")
        self.output_text.tag_configure("timestamp", foreground="#6a9955")

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg="#e8e8e8", bd=0, padx=20, pady=4)
        bar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            bar,
            text="就绪 — 选择命令后点击「执行选中命令」",
            font=(self.FONT_FAMILY, 9),
            fg=self.TEXT_SECONDARY,
            bg="#e8e8e8",
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.progress = ttk.Progressbar(
            bar,
            mode="indeterminate",
            length=120,
        )

    def select_all(self):
        for var in self.check_vars.values():
            var.set(True)
        self._log("☑ 已全选所有命令", "info")

    def deselect_all(self):
        for var in self.check_vars.values():
            var.set(False)
        self._log("☐ 已取消全选", "info")

    def relaunch_as_admin(self):
        if is_admin():
            self._log("✅ 已具备管理员权限，无需重新启动", "success")
            return
        self._log("🔄 正在以管理员身份重新启动...", "info")
        check_and_relaunch()

    def _log(self, message, tag="default"):
        """向输出框追加日志"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "success": "✔ ",
            "error": "✘ ",
            "warning": "⚠ ",
            "info": "ℹ ",
            "header": "",
            "cmd": "$ ",
            "default": "",
            "timestamp": "",
        }.get(tag, "")

        self.output_text.configure(state="normal")
        self.output_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.output_text.insert("end", f"{prefix}{message}\n", tag)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")
        self.output_lines.append(message)

    def _run_process(self, cmd_id, command):
        """执行单个命令并返回输出"""
        try:
            self._log(f"⏳ 执行: {command}", "cmd")

            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                startupinfo=startup_info,
                encoding="gbk",
                errors="replace",
                timeout=30,
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0:
                self._log(f"✅ 成功: {command}", "success")
                if stdout:
                    for line in stdout.split("\n"):
                        line = line.strip()
                        if line:
                            self._log(line, "default")
                return True
            else:
                self._log(f"❌ 失败: {command}", "error")
                if stdout:
                    for line in stdout.split("\n"):
                        line = line.strip()
                        if line:
                            self._log(line, "default")
                if stderr:
                    for line in stderr.split("\n"):
                        line = line.strip()
                        if line:
                            self._log(line, "error")
                return False

        except subprocess.TimeoutExpired:
            self._log(f"⏰ 超时: {command} 执行超过30秒", "error")
            return False
        except Exception as e:
            self._log(f"💥 异常: {str(e)}", "error")
            return False

    def _execute_worker(self):
        """后台线程执行命令"""
        selected = [cmd_id for cmd_id, var in self.check_vars.items() if var.get()]
        if not selected:
            self._log("⚠️  请至少选择一个命令", "warning")
            self._finish_execution()
            return

        # 检查管理员权限
        if not is_admin():
            self._log("⚠️  未以管理员运行！部分命令可能需要管理员权限。", "warning")

        cmd_map = {c["id"]: c for c in COMMANDS}
        self._log(f"\n{'='*50}", "header")
        self._log(f"🛜  开始执行网络恢复命令 ({len(selected)} 项)", "header")
        self._log(f"{'='*50}\n", "header")

        success_count = 0
        fail_count = 0
        needs_reboot = False

        for idx, cmd_id in enumerate(selected):
            cmd = cmd_map[cmd_id]
            self._log(f"\n--- 步骤 {idx + 1}/{len(selected)}: {cmd['label']} ---", "header")

            ok = self._run_process(cmd_id, cmd["cmd"])
            if ok:
                success_count += 1
                if cmd["needs_reboot"]:
                    needs_reboot = True
            else:
                fail_count += 1

            # 命令间短暂停顿
            time.sleep(0.3)

        # 输出汇总
        self._log(f"\n{'='*50}", "header")
        self._log(f"📊 执行汇总", "header")
        self._log(f"{'='*50}", "header")

        total = success_count + fail_count
        if fail_count == 0:
            self._log(f"✅ {success_count}/{total} 个命令全部执行成功", "success")
        else:
            self._log(f"✅ 成功: {success_count}", "success")
            self._log(f"❌ 失败: {fail_count}", "error")

        if needs_reboot:
            self._log("\n🔄 提示: 已执行需重启的命令。建议重启电脑使修改完全生效。", "warning")

        self._log("\n💡 推荐重启顺序：开始菜单 → 电源 → 重启\n", "info")

        # 更新状态
        self.root.after(0, lambda: self.status_label.configure(
            text=f"✅ 完成 — {success_count} 成功, {fail_count} 失败{' ⚠️ 建议重启' if needs_reboot else ''}"
        ))

        self._finish_execution()

    def _finish_execution(self):
        """恢复 UI 状态"""
        self.is_running = False
        self.root.after(0, lambda: self.btn_execute.configure(
            text="▶  执行选中命令",
            bg=self.ACCENT,
            state="normal",
        ))
        self.root.after(0, lambda: self.btn_select_all.configure(state="normal"))
        self.root.after(0, lambda: self.btn_deselect_all.configure(state="normal"))
        self.root.after(0, lambda: self.btn_run_admin.configure(state="normal"))
        self.root.after(0, lambda: self.progress.stop())
        self.root.after(0, lambda: self.progress.pack_forget())

    def execute_selected(self):
        if self.is_running:
            return

        self.is_running = True
        self.btn_execute.configure(text="⏳ 执行中...", bg="#666666", state="disabled")
        self.btn_select_all.configure(state="disabled")
        self.btn_deselect_all.configure(state="disabled")
        self.btn_run_admin.configure(state="disabled")
        self.progress.pack(side="right", padx=(8, 0))
        self.progress.start(10)
        self.status_label.configure(text="⏳ 正在执行命令...")

        thread = threading.Thread(target=self._execute_worker, daemon=True)
        thread.start()


# ======== 入口 ========
def main():
    root = tk.Tk()
    app = NetRecoveryTool(root)
    root.mainloop()


if __name__ == "__main__":
    # 如果以管理员身份运行，直接启动 GUI
    if is_admin():
        main()
    else:
        # 先启动 GUI，在界面上显示未提权提示，用户可点击按钮提权
        main()
