import unittest

from textual.widgets import Button, ListView, Static

from xiaozhi_control_tui.app import XiaozhiControlApp


class FakeStatus:
    def __init__(self, bridge_up: bool):
        self.bridge_up = bridge_up


class FakeController:
    def __init__(self, bridge_up: bool = True):
        self.banner = "Ready"
        self.bridge_up = bridge_up
        self.saved_runtime_updates = []

    def refresh_status(self):
        if self.banner == "Ready":
            self.banner = "Health check complete"
        return FakeStatus(self.bridge_up)

    def status_lines(self):
        return ["Bridge: UP", "LM Studio: UP", "Model: qwen3-1.7b"]

    def list_models(self):
        return ["qwen3-1.7b"]

    def managed_env(self):
        return {
            "XIAOZHI_BRIDGE_ASR_MODEL": "large-v3",
            "XIAOZHI_BRIDGE_ASR_DEVICE": "cpu",
        }

    def prepare_flash_plan(self):
        raise AssertionError("flash plan should not be requested in this test")

    def save_model_selection(self, model_name: str):
        return {"XIAOZHI_BRIDGE_MODEL_NAME": model_name}

    def save_runtime_settings(self, updates):
        self.saved_runtime_updates.append(updates)
        return updates


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_refresh_updates_widget_text(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            status_panel = app.query_one("#status-panel", Static)
            banner = app.query_one("#banner", Static)
            self.assertIn("Bridge: UP", str(status_panel.renderable))
            self.assertIn("Health check complete", str(banner.renderable))

    async def test_actions_panel_only_shows_primary_buttons(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            buttons = [button.id for button in app.query("#actions-panel Button")]
            self.assertEqual(
                buttons,
                [
                    "toggle-bridge",
                    "restart-bridge",
                    "select-model",
                    "select-asr-model",
                    "system-prompt",
                    "more-actions",
                ],
            )

    async def test_asr_button_opens_preset_popup(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_asr_model_selector()
            await pilot.pause()

            model_options = [item.name for item in app.query("#asr-model-list ListItem")]
            device_options = [item.name for item in app.query("#asr-device-list ListItem")]
            self.assertEqual(model_options, ["tiny", "base", "small", "medium", "large-v3"])
            self.assertEqual(device_options, ["cpu", "cuda"])

    async def test_asr_popup_updates_description_for_highlighted_model(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_asr_model_selector()
            await pilot.pause()

            model_list = app.query_one("#asr-model-list", ListView)
            model_list.action_cursor_up()
            await pilot.pause()

            description = str(app.query_one("#asr-model-description", Static).renderable)
            self.assertIn("Quality:", description)
            self.assertIn("Device: CPU", description)

    async def test_asr_popup_updates_description_for_selected_device(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_asr_model_selector()
            await pilot.pause()

            device_list = app.query_one("#asr-device-list", ListView)
            device_list.action_cursor_down()
            await pilot.pause()

            description = str(app.query_one("#asr-model-description", Static).renderable)
            self.assertIn("Device: CUDA", description)

    async def test_asr_popup_saves_selected_model_and_device_and_updates_banner(self):
        controller = FakeController()
        app = XiaozhiControlApp(controller=controller)
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_asr_model_selector()
            await pilot.pause()

            model_list = app.query_one("#asr-model-list", ListView)
            model_list.action_cursor_up()
            model_list.action_cursor_up()
            device_list = app.query_one("#asr-device-list", ListView)
            device_list.action_cursor_down()
            await pilot.pause()

            await pilot.click("#confirm")
            await pilot.pause()

            self.assertEqual(
                controller.saved_runtime_updates[-1],
                {
                    "XIAOZHI_BRIDGE_ASR_MODEL": "small",
                    "XIAOZHI_BRIDGE_ASR_DEVICE": "cuda",
                },
            )
            banner = app.query_one("#banner", Static)
            self.assertIn("Saved ASR config: small / cuda. Restart bridge to apply.", str(banner.renderable))

    async def test_toggle_button_label_tracks_bridge_status(self):
        controller = FakeController(bridge_up=False)
        app = XiaozhiControlApp(controller=controller)
        async with app.run_test() as pilot:
            await pilot.pause()
            toggle = app.query_one("#toggle-bridge", Button)
            self.assertEqual(str(toggle.label), "Start Bridge")

            controller.bridge_up = True
            app.refresh_status_view()
            await pilot.pause()

            toggle = app.query_one("#toggle-bridge", Button)
            self.assertEqual(str(toggle.label), "Stop Bridge")

    async def test_more_menu_lists_secondary_actions(self):
        app = XiaozhiControlApp(controller=FakeController())
        async with app.run_test() as pilot:
            await pilot.pause()
            app._open_more_actions()
            await pilot.pause()

            options = [item.name for item in app.query("#dialog-list ListItem")]
            self.assertEqual(
                options,
                [
                    "Health Check",
                    "Runtime Settings",
                    "Build Firmware",
                    "Flash Firmware",
                    "Fresh Flash",
                    "Refresh Status",
                ],
            )
