"""Local Tk desktop UI. No web server, telemetry or external assets."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import (STATE, GuardError, apply, audit, atomic_write, build_script, detect_project,
                   rollback, save_report, stage_release)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.project = tk.StringVar()
        self.build = tk.StringVar()
        self.encrypt = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="选择工程即可开始。先检查，也可以直接一键适配。")
        self.report_path = None
        self.events = queue.Queue()
        self.busy = False
        root.title("Steam Release Guard · 发布加固助手")
        root.geometry("1050x800")
        root.minsize(920, 690)
        root.configure(bg="#0e1420")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#0e1420")
        style.configure("TLabel", background="#0e1420", foreground="#dce8f5", font=("Microsoft YaHei UI", 10))
        style.configure("Hint.TLabel", foreground="#9cb1cb", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 26, "bold"), foreground="#f2f7fc")
        style.configure("TButton", padding=(14, 9), font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", background="#43d6b5", foreground="#09231e")
        style.map("Accent.TButton", background=[("active", "#7ce8ce")])
        style.configure("TCheckbutton", background="#0e1420", foreground="#dce8f5", font=("Microsoft YaHei UI", 10))
        style.map("TCheckbutton", background=[("active", "#0e1420")])
        frame = ttk.Frame(root, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="STEAM / WINDOWS / LOCAL", style="Hint.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Steam Release Guard", style="Title.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Label(frame, text="把发布配置、调试入口和资源暴露分开检查。每次修改都有可核验备份。", style="Hint.TLabel").pack(anchor="w", pady=(0, 20))
        self.path_row(frame, "工程目录", self.project)
        self.path_row(frame, "发布包目录（可选）", self.build)
        ttk.Checkbutton(frame, text="Unreal：启用 Pak 索引加密（需已有有效密钥；不等于资源内容加密）", variable=self.encrypt).pack(anchor="w", pady=(10, 12))
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(0, 10))
        self.buttons = []
        for label, action, accent in [
            ("检查工程 / 发布包", lambda: self.run("audit"), False),
            ("一键适配", lambda: self.run("apply"), True),
            ("回滚最近一次适配", self.restore, False),
            ("打开检查报告", self.open_report, False),
        ]:
            button = ttk.Button(actions, text=label, command=action, style="Accent.TButton" if accent else "TButton")
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        extra = ttk.Frame(frame)
        extra.pack(fill="x", pady=(0, 14))
        for label, action in [("生成引擎构建脚本…", self.make_build_script), ("分离调试符号…", self.stage)]:
            button = ttk.Button(extra, text=label, command=action)
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        ttk.Label(frame, textvariable=self.status, wraplength=940).pack(anchor="w", pady=(4, 10))
        box = ttk.Frame(frame)
        box.pack(fill="both", expand=True)
        self.log = tk.Text(box, bg="#172235", fg="#dce8f5", insertbackground="white", relief="flat", padx=16, pady=14,
                           font=("Microsoft YaHei UI", 10), wrap="word", height=15)
        scroll = ttk.Scrollbar(box, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.write("Unity 6：安装仅在 Editor 中使用的 IL2CPP / 非开发构建入口。\nUnreal 5：配置 Shipping，并排除发布包调试文件。\n\n适配不会自动构建、上传 Steam、生成密钥或声称无法盗版。\n构建完成后，选择实际发布包再次检查，并进行实机验收。")
        ttk.Label(frame, text="备份位于工程内 .steam-release-guard；建议关闭引擎编辑器后适配。", style="Hint.TLabel").pack(anchor="w", pady=(12, 0))
        root.after(100, self.poll)

    def path_row(self, parent, label, variable):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(4, 4))
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 4))
        ttk.Entry(row, textvariable=variable, font=("Microsoft YaHei UI", 10)).pack(side="left", fill="x", expand=True, ipady=5)
        ttk.Button(row, text="选择目录", command=lambda: self.choose(variable)).pack(side="left", padx=(8, 0))

    def choose(self, variable):
        value = filedialog.askdirectory(title="选择工程根目录" if variable is self.project else "选择实际发布包目录")
        if value:
            variable.set(value)

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_worker(self, work):
        if self.busy:
            return
        self.busy = True
        self.status.set("正在本地处理…")
        for button in self.buttons:
            button.configure(state="disabled")

        def worker():
            try:
                result = work()
                self.events.put(("done", result))
            except (GuardError, OSError, ValueError) as error:
                self.events.put(("error", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def run(self, operation):
        project_text, build_text, encrypt = self.project.get().strip(), self.build.get().strip(), self.encrypt.get()
        if not project_text:
            messagebox.showinfo("选择工程", "请先选择 Unity 或 Unreal 的工程根目录。")
            return

        def work():
            project = detect_project(project_text)
            build = Path(build_text) if build_text else None
            if build:
                audit(project, build)  # Reject invalid artifact input before mutation.
            description = []
            if operation == "apply":
                manifest = apply(project, encrypt)
                description.append(f"适配已写入，恢复记录：{manifest}" if manifest else "适配已存在，无需重复修改。")
            report = audit(project, build)
            path = save_report(report, project.root / STATE / "reports" / datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            for finding in report["findings"]:
                description.append(f"[{finding['status'].upper()}] {finding['title']}\n  {finding['detail']}")
            return ("发现需要修复的发布问题。" if report["automated_gate"] == "failed" else "自动检查完成；仍需实机与 Steam 测试分支验收。", "\n".join(description), path)

        self.start_worker(work)

    def restore(self):
        value = self.project.get().strip()
        if not value:
            messagebox.showinfo("选择工程", "请先选择工程。")
            return
        if messagebox.askyesno("恢复最近适配", "恢复最近一次适配前的文件？如果文件已被后来修改，工具会停止以保留你的修改。"):
            self.start_worker(lambda: ("已回滚；重新检查以更新报告。", str(rollback(detect_project(value))), None))

    def open_report(self):
        if self.report_path:
            webbrowser.open(self.report_path.as_uri())
        else:
            messagebox.showinfo("检查报告", "先执行一次检查或适配。")

    def make_build_script(self):
        try:
            if not self.project.get().strip():
                raise GuardError("请先选择工程。")
            project = detect_project(self.project.get())
            tool = filedialog.askopenfilename(title="选择准确版本的 Unity.exe / RunUAT.bat")
            if not tool:
                return
            output = filedialog.askdirectory(title="选择新的空构建输出目录")
            if not output:
                return
            script = build_script(project, Path(tool), Path(output))
            target = project.root / STATE / ("build-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".ps1")
            atomic_write(target, script.encode("utf-8-sig"))
            self.write(f"构建脚本已生成（尚未运行）：{target}\n在 PowerShell 中运行该文件；引擎、许可证、Windows 构建工具需已就绪。")
        except (GuardError, OSError, ValueError) as error:
            messagebox.showerror("无法生成构建脚本", str(error))

    def stage(self):
        value = self.build.get().strip()
        if not value:
            messagebox.showinfo("选择发布包", "先选择已经完成构建的发布包目录。")
            return
        release = filedialog.askdirectory(title="选择空的发布目录（与原构建目录分开）")
        if not release:
            return
        symbols = filedialog.askdirectory(title="选择空的私有符号目录（不要上传 Steam）")
        if not symbols:
            return

        def work():
            result = stage_release(Path(value), Path(release), Path(symbols))
            return ("复制校验完成；请对新的发布目录再次检查。", f"已复制并校验 {len(result['files'])} 个文件。原始文件保留。\n发布目录：{release}\n私有符号目录：{symbols}", None)

        self.start_worker(work)

    def poll(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            for button in self.buttons:
                button.configure(state="normal")
            if kind == "error":
                self.status.set("操作未完成；请查看原因。")
                self.write("ERROR: " + value)
            else:
                status, text, report = value
                self.status.set(status)
                self.write("\n" + text)
                self.report_path = report
        self.root.after(100, self.poll)


def launch():
    root = tk.Tk()
    App(root)
    root.mainloop()
