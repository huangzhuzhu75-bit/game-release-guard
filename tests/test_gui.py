"""Exercise the UI's application callbacks on a synthetic project (no game engine)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "Desktop display required")
class GuiTests(unittest.TestCase):
    def test_adapt_callback_finishes_and_produces_review_report(self):
        import tkinter as tk
        from steam_release_guard.gui import App

        with tempfile.TemporaryDirectory(prefix="srg-gui-") as temporary:
            project = Path(temporary)
            (project / "Demo.uproject").write_text('{"EngineAssociation":"5.6"}', encoding="utf-8")
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root)
                app.project.set(str(project))
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
