import asyncio
import logging
import math
import re
import struct
import time
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import websockets

from xiaozhi_bridge.asr_engine import ASREngine
from xiaozhi_bridge.audio_utils import AudioUtils
from xiaozhi_bridge.config import BridgeConfig
from xiaozhi_bridge.llm_client import LLMClient
from xiaozhi_bridge.protocol import Protocol
from xiaozhi_bridge.tts_engine import TTSEngine


VAD_THRESHOLD = 500
SILENCE_FRAMES = 10


@dataclass
class ConnectionState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: int = 1
    audio_buffer: bytearray = field(default_factory=bytearray)
    silence_counter: int = 0
    is_speaking: bool = False
    is_processing_turn: bool = False
    is_tts_streaming: bool = False
    ignore_audio_until: float = 0.0
    last_assistant_text: str = ""
    last_tts_stop_time: float = 0.0


def configure_logging(config: BridgeConfig) -> logging.Logger:
    config.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = config.log_dir / "bridge-server.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    logger = logging.getLogger("xiaozhi_bridge")
    logger.info("Bridge logging initialized at %s", log_file)
    return logger


class XiaozhiServer:
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.logger = logging.getLogger("xiaozhi_bridge.server")
        self.asr = ASREngine(config)
        self.tts = TTSEngine(config)
        self.llm = LLMClient(config)
        self.audio_utils = AudioUtils(config.ffmpeg_path)

    @staticmethod
    def _normalize_response_text(text):
        if text is None:
            return ""
        return str(text).replace("\r\n", "\n").strip()

    @staticmethod
    def _normalize_transcript(text):
        return " ".join(str(text or "").strip().split())

    @staticmethod
    def _split_sentences(text):
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part.strip() for part in parts if part.strip()]

    def _ensure_state(self, state=None):
        if state is not None:
            return state

        legacy_state = getattr(self, "_legacy_test_state", None)
        if legacy_state is None:
            legacy_state = ConnectionState(
                session_id=getattr(self, "session_id", str(uuid.uuid4())),
                protocol_version=getattr(self, "protocol_version", 1),
                audio_buffer=getattr(self, "audio_buffer", bytearray()),
                silence_counter=getattr(self, "silence_counter", 0),
                is_speaking=getattr(self, "is_speaking", False),
                last_assistant_text=getattr(self, "last_assistant_text", ""),
                last_tts_stop_time=getattr(self, "last_tts_stop_time", 0.0),
            )
            setattr(self, "_legacy_test_state", legacy_state)
        return legacy_state

    def _sync_legacy_state(self, state):
        setattr(self, "audio_buffer", state.audio_buffer)
        setattr(self, "silence_counter", state.silence_counter)
        setattr(self, "is_speaking", state.is_speaking)
        setattr(self, "session_id", state.session_id)
        setattr(self, "protocol_version", state.protocol_version)
        setattr(self, "last_assistant_text", state.last_assistant_text)
        setattr(self, "last_tts_stop_time", state.last_tts_stop_time)

    def _strip_user_echo_prefix(self, response_text, user_text):
        reply = self._normalize_response_text(response_text)
        user = self._normalize_transcript(user_text)
        if not reply or not user:
            return reply

        reply_sentences = self._split_sentences(reply)
        normalized_user = user.lower().rstrip("?.!")
        while reply_sentences:
            first_sentence = reply_sentences[0]
            normalized_first = self._normalize_transcript(first_sentence).lower().rstrip("?.!")
            similarity = SequenceMatcher(None, normalized_first, normalized_user).ratio()
            if normalized_first.startswith(normalized_user) or similarity >= 0.85:
                reply_sentences = reply_sentences[1:]
                continue
            break
        return " ".join(reply_sentences).strip()

    def _postprocess_response_text(self, response_text, user_text):
        reply = self._normalize_response_text(response_text)
        reply = self._strip_user_echo_prefix(reply, user_text)
        if not reply:
            return ""

        sentences = self._split_sentences(reply)
        if not sentences:
            return ""

        trimmed = " ".join(sentences[: self.config.max_reply_sentences]).strip()
        if len(trimmed) <= self.config.max_reply_chars:
            return trimmed

        cutoff = trimmed[: self.config.max_reply_chars].rstrip(" ,;:")
        last_sentence_break = max(cutoff.rfind("."), cutoff.rfind("?"), cutoff.rfind("!"))
        if last_sentence_break >= 20:
            cutoff = cutoff[: last_sentence_break + 1].strip()
        return cutoff.strip()

    def _should_ignore_transcript(self, text, now=None, state=None):
        state = self._ensure_state(state)
        transcript = self._normalize_transcript(text).lower()
        if len(transcript.replace(" ", "")) < 2:
            return True
        if not state.last_assistant_text or state.last_tts_stop_time <= 0:
            return False

        current_time = time.monotonic() if now is None else now
        elapsed_ms = (current_time - state.last_tts_stop_time) * 1000.0
        if elapsed_ms < 0 or elapsed_ms > self.config.tts_echo_guard_ms:
            return False

        assistant_text = self._normalize_transcript(state.last_assistant_text).lower()
        similarity = SequenceMatcher(None, transcript, assistant_text).ratio()
        if similarity >= self.config.echo_similarity_threshold:
            self.logger.info(
                "Ignoring likely TTS echo transcript similarity=%.3f elapsed_ms=%.1f text=%s",
                similarity,
                elapsed_ms,
                text,
            )
            return True
        return False

    async def _send_json_event(self, websocket, payload, summary):
        await websocket.send(payload)
        self.logger.info("Sent JSON event: %s", summary)

    async def _stream_tts_audio(self, websocket, opus_packets):
        async def packet_stream():
            for packet in opus_packets:
                yield packet

        return await self._stream_tts_packet_stream(websocket, packet_stream())

    async def _stream_tts_packet_stream(self, websocket, packet_stream, state=None):
        state = self._ensure_state(state)
        packet_interval = self.config.frame_duration / 1000.0
        sent_packets = 0
        async for packet in packet_stream:
            if sent_packets == 0:
                self.logger.info("Streaming first opus packet back to device")
            await websocket.send(Protocol.wrap_audio_payload(packet, self.protocol_version))
            sent_packets += 1
            await asyncio.sleep(packet_interval)

        if sent_packets == 0:
            self.logger.warning("No opus packets generated for TTS")
            await self._send_json_event(websocket, Protocol.create_tts_stop(), "tts stop (empty audio)")
            return 0

        self.logger.info("Streaming %s opus packets back to device", sent_packets)
        await self._send_json_event(websocket, Protocol.create_tts_stop(), "tts stop")
        state.last_tts_stop_time = time.monotonic()
        echo_guard_ms = getattr(self.config, "tts_echo_guard_ms", 1200)
        state.ignore_audio_until = state.last_tts_stop_time + (echo_guard_ms / 1000.0)
        self._sync_legacy_state(state)
        return sent_packets

    async def handle_connection(self, websocket):
        self.logger.info("New connection from %s", websocket.remote_address)
        state = ConnectionState()
        self.llm.start_session(state.session_id)

        try:
            async for message in websocket:
                msg_type, data = Protocol.parse_message(message)

                if msg_type == "json":
                    await self.handle_json(websocket, data, state)
                elif msg_type == "audio":
                    await self.handle_audio(websocket, data, state)
                else:
                    self.logger.warning("Unknown message type")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Connection closed")
        except Exception as exc:
            self.logger.exception("Bridge connection error: %s", exc)
        finally:
            self.llm.end_session(state.session_id)

    async def handle_json(self, websocket, data, state=None):
        state = self._ensure_state(state)
        self.logger.info("Received JSON: %s", data)
        msg_type = data.get("type")

        if msg_type == "hello":
            version = int(data.get("version", 1) or 1)
            state.protocol_version = version if version in (1, 3) else 1
            response = Protocol.create_hello_response(
                state.session_id,
                version=state.protocol_version,
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                frame_duration=self.config.frame_duration,
                server_id=self.config.server_id,
                server_name=self.config.discovery_host,
            )
            await websocket.send(response)
            self.logger.info("Sent hello response with protocol version %s", state.protocol_version)
            self._sync_legacy_state(state)

    async def handle_audio(self, websocket, opus_data, state=None):
        state = self._ensure_state(state)
        now = time.monotonic()
        if now < state.ignore_audio_until:
            return
        if state.is_processing_turn and self.config.drop_audio_while_processing:
            return
        if state.is_tts_streaming and self.config.drop_audio_while_tts:
            return

        pcm = self.audio_utils.decode_opus(opus_data)
        if not pcm:
            return

        shorts = struct.unpack(f"{len(pcm) // 2}h", pcm)
        if not shorts:
            return
        sum_squares = sum(sample * sample for sample in shorts)
        rms = math.sqrt(sum_squares / len(shorts))

        if rms > VAD_THRESHOLD:
            state.silence_counter = 0
            state.is_speaking = True
            state.audio_buffer.extend(pcm)
        elif state.is_speaking:
            state.silence_counter += 1
            state.audio_buffer.extend(pcm)

            if state.silence_counter > SILENCE_FRAMES:
                await self.process_speech(websocket, state)

        self._sync_legacy_state(state)

    async def process_speech(self, websocket, state=None):
        state = self._ensure_state(state)
        if state.is_processing_turn or not state.audio_buffer:
            return

        state.is_processing_turn = True
        self.logger.info("Silence detected, processing speech")
        try:
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(None, self.asr.transcribe, bytes(state.audio_buffer))

            if not text:
                self.logger.info("No speech recognized")
                return

            text = self._normalize_transcript(text)
            if self._should_ignore_transcript(text, time.monotonic(), state):
                return

            self.logger.info("ASR recognized: %s", text)
            await self._send_json_event(
                websocket,
                Protocol.create_stt_text(text, state.session_id),
                f"stt text len={len(text)}",
            )

            self.logger.info("Asking LLM")
            llm_response = await self.llm.get_response(state.session_id, text)
            llm_response = self._postprocess_response_text(llm_response, text)
            if not llm_response:
                llm_response = "Xin loi, toi chua co cau tra loi phu hop."
                self.logger.warning("LLM returned empty content, using fallback response")
            state.last_assistant_text = llm_response
            self.logger.info("LLM response: %s", llm_response)

            await self._send_json_event(websocket, Protocol.create_tts_start(), "tts start")
            await self._send_json_event(
                websocket,
                Protocol.create_tts_sentence_start(llm_response),
                f"tts sentence_start len={len(llm_response)}",
            )

            state.is_tts_streaming = True
            mp3_stream = self.tts.stream_audio(llm_response)
            opus_packet_stream = self.audio_utils.stream_mp3_to_opus_packets(mp3_stream)
            await self._stream_tts_packet_stream(websocket, opus_packet_stream, state)
        except Exception as exc:
            self.logger.exception("Error streaming TTS: %s", exc)
        finally:
            state.is_tts_streaming = False
            state.is_processing_turn = False
            state.is_speaking = False
            state.audio_buffer = bytearray()
            state.silence_counter = 0
            self._sync_legacy_state(state)


async def run_server():
    config = BridgeConfig.from_env()
    logger = configure_logging(config)
    server = XiaozhiServer(config)
    async with websockets.serve(server.handle_connection, config.host, config.port):
        logger.info("Xiaozhi Bridge Server running on ws://%s:%s", config.host, config.port)
        await asyncio.Future()


def main():
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logging.getLogger("xiaozhi_bridge.server").info("Server stopped")


if __name__ == "__main__":
    main()
