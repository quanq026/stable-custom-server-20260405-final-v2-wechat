import unittest
from unittest.mock import Mock, patch

from xiaozhi_control_tui.lmstudio import LMStudioClient


class LMStudioClientTests(unittest.TestCase):
    @patch("xiaozhi_control_tui.lmstudio.httpx.get")
    def test_list_models_extracts_and_sorts_ids(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "data": [{"id": "qwen3-1.7b"}, {"id": "qwen2.5-14b-instruct-1m"}]
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        client = LMStudioClient("http://localhost:1234/v1/models")
        models = client.list_models()

        self.assertEqual(models, ["qwen2.5-14b-instruct-1m", "qwen3-1.7b"])

    @patch("xiaozhi_control_tui.lmstudio.httpx.get", side_effect=RuntimeError("boom"))
    def test_is_reachable_returns_false_on_error(self, _mock_get):
        client = LMStudioClient("http://localhost:1234/v1/models")
        self.assertFalse(client.is_reachable())
