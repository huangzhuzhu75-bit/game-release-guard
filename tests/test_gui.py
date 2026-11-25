"""Exercise the UI's application callbacks on a synthetic project (no game engine)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "Desktop display required")
class GuiTests(unittest.TestCase):
    def wait_for_worker(self, root, app):
        deadline = time.monotonic() + 15
        while app.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.01)
        self.assertFalse(app.busy, app.log.get("1.0", "end"))

    def test_full_backup_and_restore_buttons_produce_verified_new_project(self):
        import tkinter as tk
        from steam_release_guard.gui import App
        from steam_release_guard import project_backup
        with tempfile.TemporaryDirectory(prefix="srg-gui-full-") as temporary:
            base = Path(temporary)
            project = base / "project"
            project.mkdir()
            descriptor = b'{"EngineAssociation":"5.6"}'
            (project / "Demo.uproject").write_bytes(descriptor)
            (project / "asset.bin").write_bytes(b"user resource")
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root)
                app.project.set(str(project))
                app.backup_dir.set(str(base / "backups"))
                with mock.patch("steam_release_guard.gui.messagebox.askyesno", return_value=True):
                    app.make_backup()
                    self.wait_for_worker(root, app)
                snapshot = next((base / "backups").iterdir())
                self.assertEqual(project_backup.verify(snapshot)["status"], "VERIFIED")
                self.assertIn(snapshot.name, app.backup_note.get())
                self.assertEqual(float(app.progress["value"]), 100)
                with mock.patch("steam_release_guard.gui.filedialog.askdirectory", side_effect=[str(snapshot), str(base)]), \
                     mock.patch("steam_release_guard.gui.messagebox.askyesno", return_value=True):
                    app.restore_backup()
                    self.wait_for_worker(root, app)
                restored = next(p for p in base.glob("RestoredProject-*") if p.is_dir())
                self.assertEqual((restored / "Demo.uproject").read_bytes(), descriptor)
                self.assertEqual((restored / "asset.bin").read_bytes(), b"user resource")
                self.assertEqual((project / "asset.bin").read_bytes(), b"user resource")
                self.assertTrue(all(str(button["state"]) == "normal" for button in app.buttons))
            finally:
                root.destroy()

    def test_full_backup_failure_blocks_gui_adaptation(self):
        import tkinter as tk
        from steam_release_guard.gui import App
        with tempfile.TemporaryDirectory(prefix="srg-gui-block-") as temporary:
            base = Path(temporary)
            project = base / "project"
            project.mkdir()
            (project / "Demo.uproject").write_text('{"EngineAssociation":"5.6"}', encoding="utf-8")
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root)
                app.project.set(str(project))
                with mock.patch("steam_release_guard.gui.messagebox.askyesno", return_value=True), \
                     mock.patch("steam_release_guard.project_backup._copy", side_effect=PermissionError("private text")):
                    app.run("apply")
                    self.wait_for_worker(root, app)
                self.assertFalse((project / "Config/DefaultGame.ini").exists())
                self.assertFalse((project / ".gitignore").exists())
                self.assertIn("Full backup failed", app.log.get("1.0", "end"))
                self.assertNotIn("private text", app.log.get("1.0", "end"))
                self.assertIsNone(app.report_path)
                self.assertTrue(all(str(button["state"]) == "normal" for button in app.buttons))
            finally:
                root.destroy()

    def test_unexpected_worker_failure_restores_controls_without_leaking_message(self):
        import tkinter as tk
        from steam_release_guard.gui import App
        root = tk.Tk()
        root.withdraw()
        try:
            app = App(root)

            def fail():
                raise RuntimeError("private-password-must-not-be-logged")
            app.start_worker(fail)
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            self.assertFalse(app.busy)
            self.assertTrue(all(str(button["state"]) == "normal" for button in app.buttons))
            self.assertEqual(str(app.cancel_button["state"]), "disabled")
            self.assertIn("RuntimeError", app.log.get("1.0", "end"))
            self.assertNotIn("private-password", app.log.get("1.0", "end"))
        finally:
            root.destroy()

    def test_adapt_callback_finishes_and_produces_review_report(self):
        import tkinter as tk
        from steam_release_guard.gui import App

        with tempfile.TemporaryDirectory(prefix="srg-gui-") as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            (project / "Demo.uproject").write_text('{"EngineAssociation":"5.6"}', encoding="utf-8")
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root)
                app.project.set(str(project))
                with mock.patch("steam_release_guard.gui.messagebox.askyesno", return_value=True):
                    app.run("apply")
                deadline = time.monotonic() + 15
                while app.busy and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.01)
                self.assertFalse(app.busy, "UI worker failed to finish")
                self.assertIsNotNone(app.report_path, app.log.get("1.0", "end"))
                report = json.loads(app.report_path.with_suffix(".json").read_text(encoding="utf-8"))
                self.assertEqual(report["release_status"], "REQUIRES_MANUAL_REVIEW")
                self.assertIn("PPBC_Shipping", (project / "Config/DefaultGame.ini").read_text(encoding="utf-8"))
                self.assertTrue(all(str(button["state"]) == "normal" for button in app.buttons))
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
