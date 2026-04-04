import unittest

from textual.widgets import Static

from xiaozhi_control_tui.app import XiaozhiControlApp


class FakeController:
    def __init__(self):
        self.banner = "Ready"

    def refresh_status(self):
        self.banner = "Health check complete"
        return object()

    def status_lines(self):
        return ["Bridge: UP", "LM Studio: UP", "Model: qwen3-1.7b"]


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_refresh_updates_widget_text(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            status_panel = app.query_one("#status-panel", Static)
            banner = app.query_one("#banner", Static)
            self.assertIn("Bridge: UP", str(status_panel.renderable))
            self.assertIn("Health check complete", str(banner.renderable))
