import importlib.util
from pathlib import Path
import os

import numpy as np


def collect_windows_gpu_runtime_dirs(site_packages_root: Path) -> list[Path]:
    runtime_dirs: list[Path] = []

    ctranslate2_dir = site_packages_root / "ctranslate2"
    if any(ctranslate2_dir.glob("*.dll")):
        runtime_dirs.append(ctranslate2_dir)

    nvidia_root = site_packages_root / "nvidia"
    if nvidia_root.exists():
        for package_dir in sorted(nvidia_root.iterdir()):
            bin_dir = package_dir / "bin"
            if bin_dir.is_dir() and any(bin_dir.glob("*.dll")):
                runtime_dirs.append(bin_dir)

    return runtime_dirs


def prepare_windows_gpu_runtime() -> None:
    if os.name != "nt":
        return

    ctranslate2_spec = importlib.util.find_spec("ctranslate2")
    if ctranslate2_spec is None or ctranslate2_spec.origin is None:
        return

    site_packages_root = Path(ctranslate2_spec.origin).resolve().parent.parent
    runtime_dirs = collect_windows_gpu_runtime_dirs(site_packages_root)
    if not runtime_dirs:
        return

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    path_entry_set = {entry.lower() for entry in path_entries if entry}

    for runtime_dir in runtime_dirs:
        runtime_dir_str = str(runtime_dir)
        if runtime_dir_str.lower() not in path_entry_set:
            path_entries.insert(0, runtime_dir_str)
            path_entry_set.add(runtime_dir_str.lower())
        add_dll_directory = getattr(os, "add_dll_directory", None)
        if add_dll_directory is not None:
            add_dll_directory(runtime_dir_str)

    os.environ["PATH"] = os.pathsep.join(path_entries)


class ASREngine:
    def __init__(self, config):
        print(
            f"Loading Whisper model: {config.asr_model} on {config.asr_device}/{config.asr_compute_type} "
            f"for language={config.asr_language}",
            flush=True,
        )
        if os.name == "nt" and config.asr_device.lower() == "cuda":
            prepare_windows_gpu_runtime()
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            config.asr_model,
            device=config.asr_device,
            compute_type=config.asr_compute_type,
        )
        self.language = config.asr_language

    def transcribe(self, audio_data):
        """
        Transcribe audio data (bytes) to text.
        audio_data: Raw PCM 16kHz mono samples (bytes)
        """
        if not audio_data:
            return ""

        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self.model.transcribe(audio_array, beam_size=5, language=self.language)
        text = " ".join(segment.text for segment in segments)
        return text.strip()
