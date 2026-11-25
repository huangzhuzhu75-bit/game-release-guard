"""Local Tk desktop UI. No web server, telemetry or external assets."""
from __future__ import annotations

import queue
import json
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import (STATE, GuardError, apply, audit, atomic_write, build_script, detect_project,
                   plan, rollback, save_report, stage_release)
from .operations import Operation, safe_error, writer
from .transactions import rollback_preview
from . import project_backup


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.project = tk.StringVar()
        self.build = tk.StringVar()
        self.encrypt = tk.BooleanVar(value=False)
        self.backup_dir = tk.StringVar()
        self.backup_note = tk.StringVar(value="完整备份：默认存到工程旁的 .srg-backups 目录；适配前自动复制并核验。")
        self.status = tk.StringVar(value="选择工程即可开始。先检查，也可以直接一键适配。")
        self.report_path = None
        self.events = queue.Queue()
        self.busy = False
        self.operation = None
        self.closing = False
        root.protocol("WM_DELETE_WINDOW", self.close)
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
        frame = ttk.Frame(root, padding=20)
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
        for label, action in [("完整备份", self.make_backup), ("恢复完整备份…", self.restore_backup),
                              ("备份位置…", self.choose_backup_dir),
                              ("生成构建脚本…", self.make_build_script), ("分离调试符号…", self.stage)]:
            button = ttk.Button(extra, text=label, command=action)
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        ttk.Label(frame, textvariable=self.backup_note, wraplength=980, style="Hint.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, textvariable=self.status, wraplength=940).pack(anchor="w", pady=(4, 10))
        progress_row = ttk.Frame(frame)
        progress_row.pack(fill="x", pady=(0, 8))
        self.progress = ttk.Progressbar(progress_row, maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)
        self.cancel_button = ttk.Button(progress_row, text="取消", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right", padx=(8, 0))
        box = ttk.Frame(frame)
        box.pack(fill="both", expand=True)
        self.log = tk.Text(box, bg="#172235", fg="#dce8f5", insertbackground="white", relief="flat", padx=16, pady=14,
                           font=("Microsoft YaHei UI", 10), wrap="word", height=15)
        scroll = ttk.Scrollbar(box, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.write("Unity 6：安装仅在 Editor 中使用的 IL2CPP / 非开发构建入口。\nUnreal 5：配置 Shipping，并排除发布包调试文件。\n\n适配不会自动构建、上传 Steam、生成密钥或声称无法盗版。\n构建完成后，选择实际发布包再次检查，并进行实机验收。")
        ttk.Label(frame, text="先关闭引擎和同步工具。完整备份在工程外；逐文件回滚记录仍在工程内 .steam-release-guard。", style="Hint.TLabel").pack(anchor="w", pady=(8, 0))
        self.poll_id = root.after(100, self.poll)
        root.bind("<Destroy>", self.on_destroy, add="+")

    def on_destroy(self, event):
        if event.widget is self.root:
            self.root.after_cancel(self.poll_id)

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

    def choose_backup_dir(self):
        value = filedialog.askdirectory(title="选择工程外的完整备份存放目录（可与工程不同磁盘）")
        if value:
            self.backup_dir.set(value)
            self.backup_note.set("完整备份存放目录：" + value)

    def make_backup(self):
        try:
            if not self.project.get().strip():
                raise GuardError("请先选择工程。")
            project = detect_project(self.project.get())
            destination = project_backup.backup_root(project, self.backup_dir.get() or None)
            if not messagebox.askyesno("完整备份工程", f"原工程：{project.root}\n备份存放目录：{destination}\n\n复制工程目录内全部文件，包括隐藏文件、缓存和资源；需要足够磁盘空间。\n请先关闭编辑器和同步工具。完成逐文件核验后才标记成功。继续？"):
                return

            def work():
                result = project_backup.create(project, destination, operation=self.operation)
                return ("完整备份已核验；原工程未修改。", f"已核验 {result['file_count']} 个文件。\n完整备份：{result['backup_path']}\n恢复时请选择新的工程目录。", None)
            self.start_worker(work)
        except Exception as error:
            messagebox.showerror("无法备份", safe_error(error))

    def restore_backup(self):
        try:
            source = filedialog.askdirectory(title="选择带 srg-project-backup.json 的日期备份目录")
            if not source:
                return
            parent = filedialog.askdirectory(title="选择恢复副本的存放目录（会创建新子目录，不覆盖原工程）")
            if not parent:
                return
            target = Path(parent) / ("RestoredProject-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            preview = project_backup.restore_preview(source, target)
            if not messagebox.askyesno("恢复到新工程目录", f"完整备份：{source}\n新工程：{target}\n文件数：{preview['file_count']}\n\n先核验全部备份，再复制并核验恢复结果。原工程保留。继续？"):
                return

            def work():
                result = project_backup.restore(source, target, operation=self.operation, expected_preview=preview)
                return ("完整恢复已核验；请先打开恢复副本检查。", f"新工程目录：{result['output']}\n恢复记录：{result['receipt']}\n原工程和备份均保留。", None)
            self.start_worker(work)
        except Exception as error:
            messagebox.showerror("无法恢复完整备份", safe_error(error))

    def start_worker(self, work):
        if self.busy:
            return
        self.busy = True
        self.report_path = None
        self.progress["value"] = 0
        self.operation = Operation(lambda event: self.events.put(("progress", event)))
        self.cancel_button.configure(state="normal")
        self.status.set("正在本地处理…")
        for button in self.buttons:
            button.configure(state="disabled")

        def worker():
            try:
                result = work()
                self.events.put(("done", result))
            except BaseException as error:
                self.events.put(("error", safe_error(error)))

        threading.Thread(target=worker, daemon=False).start()

    def cancel(self):
        if self.busy and self.operation and self.operation.cancellable:
            self.operation.cancel.set()
            self.status.set("已请求取消；等待当前校验完成，保留原文件和恢复记录。")

    def close(self):
        if not self.busy:
            self.root.destroy()
            return
        self.closing = True
        self.cancel()
        if self.operation and not self.operation.cancellable:
            self.status.set("当前正在提交，不能取消。完成恢复记录后关闭窗口。")

    def run(self, operation):
        project_text, build_text, encrypt = self.project.get().strip(), self.build.get().strip(), self.encrypt.get()
        backup_dir = self.backup_dir.get() or None
        if not project_text:
            messagebox.showinfo("选择工程", "请先选择 Unity 或 Unreal 的工程根目录。")
            return
        try:
            preview = None
            if operation == "apply":
                project = detect_project(project_text)
                preview = plan(project, encrypt)
                summary = "\n".join(f"• {c.path}: {c.purpose}" for c in preview) or "配置已存在；仅更新检查报告。"
                destination = project_backup.backup_root(project, backup_dir)
                backup_text = f"先完整备份工程内所有文件到：\n{destination}\n校验失败将停止适配。请先关闭编辑器和同步工具。" if preview else "工程无需修改，本次不重复创建完整备份。"
                if not messagebox.askyesno("确认适配范围", f"{project.engine} {project.version}\n{summary}\n\n{backup_text}\n项目写入阶段不可取消。继续？"):
                    return
        except Exception as error:
            messagebox.showerror("无法预览", safe_error(error))
            return

        def work():
            project = detect_project(project_text)
            build = Path(build_text) if build_text else None
            if build:
                audit(project, build, operation=self.operation)  # Reject invalid artifact input before mutation.
            description = []
            if operation == "apply":
                manifest = apply(project, encrypt, operation=self.operation, expected_plan=preview, backup_dir=backup_dir)
                description.append(f"适配已写入，恢复记录：{manifest}" if manifest else "适配已存在，无需重复修改。")
                if manifest:
                    full = json.loads(manifest.read_text(encoding="utf-8"))["full_backup"]
                    description.append(f"完整工程备份已核验：{full['backup_path']}")
            self.operation.step("检查工程和发布包", cancellable=operation != "apply")
            report = audit(project, build, operation=self.operation if operation == "audit" else None)
            self.operation.step("保存检查报告", cancellable=False)
            path = save_report(report, project.root / STATE / "reports" / datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
            for finding in report["findings"]:
                description.append(f"[{finding['status'].upper()}] {finding['title']}\n  {finding['detail']}")
            return ("发现需要修复的发布问题。" if report["automated_gate"] == "failed" else "自动检查完成；仍需实机与 Steam 测试分支验收。", "\n".join(description), path)

        def locked_work():
            with writer():
                return work()
        self.start_worker(locked_work)

    def restore(self):
        value = self.project.get().strip()
        if not value:
            messagebox.showinfo("选择工程", "请先选择工程。")
            return
        try:
            project = detect_project(value)
            preview = rollback_preview(project)
            if messagebox.askyesno("恢复最近适配", "将恢复：\n" + "\n".join(preview["files"]) + "\n\n后续修改会阻止回滚。写入阶段不可取消。继续？"):
                self.start_worker(lambda: ("已回滚；重新检查以更新报告。", str(rollback(project, operation=self.operation, expected_preview=preview)), None))
        except Exception as error:
            messagebox.showerror("无法预览回滚", safe_error(error))

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
            if not messagebox.askyesno("保存构建脚本", f"保存到：{target}\n引擎：{tool}\n输出：{output}\n只保存，不运行。继续？"):
                return
            with writer(project):
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(script.encode("utf-8-sig"))
            self.write(f"构建脚本已生成（尚未运行）：{target}\n在 PowerShell 中运行该文件；引擎、许可证、Windows 构建工具需已就绪。")
        except Exception as error:
            messagebox.showerror("无法生成构建脚本", safe_error(error))

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
        if not messagebox.askyesno("确认暂存范围", f"原构建：{value}\n发布副本：{release}\n私有符号：{symbols}\n\n复制全部构建文件，按符号规则分离；原文件保留，目标必须为空。继续？"):
            return

        def work():
            result = stage_release(Path(value), Path(release), Path(symbols), operation=self.operation)
            return ("复制校验完成；请对新的发布目录再次检查。", f"已复制并校验 {len(result['files'])} 个文件。原始文件保留。\n发布目录：{release}\n私有符号目录：{symbols}", None)

        self.start_worker(work)

    def poll(self):
        for _ in range(100):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                if value.get("backup_path"):
                    self.backup_note.set("已核验完整备份：" + value["backup_path"])
                    self.write(self.backup_note.get())
                self.progress["value"] = 100 * value["current"] / max(1, value["total"])
                self.status.set(f"{value['phase']} ({value['current']}/{value['total']})" + ("" if value["cancellable"] else " · 当前阶段不可取消"))
                self.cancel_button.configure(state="normal" if value["cancellable"] else "disabled")
                continue
            self.busy = False
            self.cancel_button.configure(state="disabled")
            for button in self.buttons:
                button.configure(state="normal")
            if kind == "error":
                self.status.set("操作未完成；请查看原因。")
                self.write("ERROR: " + value)
            else:
                status, text, report = value
                self.progress["value"] = 100
                self.status.set(status)
                self.write("\n" + text)
                self.report_path = report
        if self.closing and not self.busy:
            self.root.destroy()
            return
        self.poll_id = self.root.after(100, self.poll)


def launch():
    root = tk.Tk()
    App(root)
    root.mainloop()
