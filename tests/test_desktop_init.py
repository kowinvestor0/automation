import tkinter as tk
import unittest
from desktop.app import ControlPanel


class TestDesktopInit(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_init_with_empty_config(self):
        app = ControlPanel.__new__(ControlPanel)
        app.root = self.root
        app.cfg = {
            "workspace": "",
            "publish": {},
            "run": {},
            "notify": {},
            "github": {},
            "keys": {},
        }
        app._load_settings = lambda: app.cfg
        ControlPanel.__init__(app, self.root)
        self.assertTrue(app.ready)
        self.assertEqual(app.secret("NON_EXISTENT_KEY"), "")

    def test_init_with_default_config(self):
        app = ControlPanel(self.root)
        self.assertTrue(app.ready)
