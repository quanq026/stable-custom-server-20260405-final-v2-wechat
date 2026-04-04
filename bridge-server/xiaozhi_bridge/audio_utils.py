import asyncio
import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _configure_opus_dll_path():
    if sys.platform != "win32":
        return

    candidates = [
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parents[1] / ".venv" / "Scripts",
    ]
    for candidate in candidates:
        opus_dll = candidate / "opus.dll"
        if opus_dll.exists():
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            os.add_dll_directory(str(candidate))
            return


_configure_opus_dll_path()

import opuslib

class AudioUtils:
    def __init__(self, ffmpeg_path=""):
        # Initialize Opus encoder/decoder
        # Sample rate: 16000, Channels: 1
        self.encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_VOIP)
        self.decoder = opuslib.Decoder(16000, 1)
        self.frame_size_bytes = 960 * 2
        self.ffmpeg_path = ffmpeg_path or self._resolve_ffmpeg_path()

    def _resolve_ffmpeg_path(self):
        candidates = [
            shutil.which("ffmpeg"),
            os.getenv("FFMPEG_PATH"),
            r"C:\Program Files\ShareX\ffmpeg.exe",
        ]

        winget_root = Path(
            r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages"
            r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        )
        if winget_root.exists():
            candidates.extend(str(path) for path in winget_root.rglob("ffmpeg.exe"))

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate

        raise FileNotFoundError("ffmpeg.exe not found. Set XIAOZHI_BRIDGE_FFMPEG_PATH or install ffmpeg.")

    def decode_opus(self, opus_data):
        """
        Decode Opus packet to PCM.
        """
        try:
            pcm = self.decoder.decode(opus_data, 960) # 960 samples = 60ms at 16kHz
            return pcm
        except opuslib.OpusError:
            return b""

    def encode_pcm_to_opus(self, pcm_data):
        """
        Encode PCM data (bytes) to Opus packet.
        Frame size must be 960 samples (60ms) for 16kHz.
        """
        try:
            opus_packet = self.encoder.encode(pcm_data, 960)
            return opus_packet
        except opuslib.OpusError as e:
            print(f"Opus encoding error: {e}")
            return b""

    def mp3_to_opus_packets(self, mp3_file):
        """
        Convert MP3 file to a list of Opus packets (bytes).
        1. MP3 -> PCM (via ffmpeg)
        2. PCM -> Opus packets
        """
        # 1. Convert to PCM 16kHz Mono 16-bit
        process = subprocess.Popen(
            [self.ffmpeg_path, '-y', '-i', mp3_file, '-f', 's16le', '-ac', '1', '-ar', '16000', 'pipe:1'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        pcm_data, _ = process.communicate()

        packets = []
        frame_size = self.frame_size_bytes
        
        # 2. Chunk PCM and encode
        for i in range(0, len(pcm_data), frame_size):
            chunk = pcm_data[i:i+frame_size]
            if len(chunk) < frame_size:
                # Pad with silence if last chunk is incomplete
                chunk += b'\x00' * (frame_size - len(chunk))
            
            opus_packet = self.encode_pcm_to_opus(chunk)
            if opus_packet:
                packets.append(opus_packet)
                
        return packets

    def packetize_pcm_bytes(self, pcm_bytes, remainder=b"", flush=False):
        buffer = bytearray(remainder)
        buffer.extend(pcm_bytes)

        packets = []
        while len(buffer) >= self.frame_size_bytes:
            chunk = bytes(buffer[: self.frame_size_bytes])
            del buffer[: self.frame_size_bytes]
            opus_packet = self.encode_pcm_to_opus(chunk)
            if opus_packet:
                packets.append(opus_packet)

        if flush and buffer:
            chunk = bytes(buffer) + (b"\x00" * (self.frame_size_bytes - len(buffer)))
            opus_packet = self.encode_pcm_to_opus(chunk)
            if opus_packet:
                packets.append(opus_packet)
            buffer.clear()

        return packets, bytes(buffer)

    async def _feed_ffmpeg_stdin(self, stdin, mp3_stream):
        try:
            async for chunk in mp3_stream:
                if not chunk:
                    continue
                stdin.write(chunk)
                await stdin.drain()
        finally:
            if not stdin.is_closing():
                stdin.close()

    async def stream_mp3_to_opus_packets(self, mp3_stream):
        process = await asyncio.create_subprocess_exec(
            self.ffmpeg_path,
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        remainder = b""
        writer_task = asyncio.create_task(self._feed_ffmpeg_stdin(process.stdin, mp3_stream))

        try:
            while True:
                pcm_chunk = await process.stdout.read(4096)
                if not pcm_chunk:
                    break
                packets, remainder = self.packetize_pcm_bytes(pcm_chunk, remainder, flush=False)
                for packet in packets:
                    yield packet

            packets, remainder = self.packetize_pcm_bytes(b"", remainder, flush=True)
            for packet in packets:
                yield packet

            await writer_task
            stderr_output = await process.stderr.read()
            return_code = await process.wait()
            if return_code != 0:
                message = stderr_output.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(f"ffmpeg stream decode failed with code {return_code}: {message}")
        finally:
            if not writer_task.done():
                writer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await writer_task
            if process.returncode is None:
                process.kill()
                await process.wait()
