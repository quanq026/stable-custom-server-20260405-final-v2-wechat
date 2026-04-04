import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(r"C:\QuanNewData\xiaozhi\Xiaozhi-ESP32-Bridge-Server\.worktrees\codex\bridge-server-lan")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from xiaozhi_bridge.audio_utils import AudioUtils


class AudioUtilsStreamingTests(unittest.TestCase):
    def test_packetize_pcm_bytes_yields_packets_when_frame_fills(self):
        audio = AudioUtils.__new__(AudioUtils)
        audio.frame_size_bytes = 1920
        encoded_chunks = []
        audio.encode_pcm_to_opus = lambda chunk: encoded_chunks.append(chunk) or b"pkt"

        packets, remainder = AudioUtils.packetize_pcm_bytes(
            audio, b"b" * 1000, remainder=b"a" * 1000, flush=False
        )

        self.assertEqual(packets, [b"pkt"])
        self.assertEqual(remainder, b"b" * 80)
        self.assertEqual(len(encoded_chunks[0]), 1920)

    def test_packetize_pcm_bytes_flushes_final_partial_frame(self):
        audio = AudioUtils.__new__(AudioUtils)
        audio.frame_size_bytes = 1920
        encoded_chunks = []
        audio.encode_pcm_to_opus = lambda chunk: encoded_chunks.append(chunk) or b"pkt"

        packets, remainder = AudioUtils.packetize_pcm_bytes(audio, b"a" * 400, b"", flush=True)

        self.assertEqual(packets, [b"pkt"])
        self.assertEqual(remainder, b"")
        self.assertEqual(len(encoded_chunks[0]), 1920)


if __name__ == "__main__":
    unittest.main()
