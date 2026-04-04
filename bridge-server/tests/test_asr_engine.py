from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from xiaozhi_bridge import asr_engine


class TestAsrEngineRuntimePaths(unittest.TestCase):
    def test_collects_windows_gpu_runtime_dirs_from_site_packages(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctranslate2_dir = root / "ctranslate2"
            ctranslate2_dir.mkdir(parents=True)
            (ctranslate2_dir / "cudnn64_9.dll").write_bytes(b"")

            cublas_bin = root / "nvidia" / "cublas" / "bin"
            cublas_bin.mkdir(parents=True)
            (cublas_bin / "cublas64_12.dll").write_bytes(b"")

            nvrtc_bin = root / "nvidia" / "cuda_nvrtc" / "bin"
            nvrtc_bin.mkdir(parents=True)
            (nvrtc_bin / "nvrtc64_120_0.dll").write_bytes(b"")

            dirs = asr_engine.collect_windows_gpu_runtime_dirs(root)

            self.assertEqual(
                dirs,
                [
                    ctranslate2_dir,
                    cublas_bin,
                    nvrtc_bin,
                ],
            )


if __name__ == "__main__":
    unittest.main()
