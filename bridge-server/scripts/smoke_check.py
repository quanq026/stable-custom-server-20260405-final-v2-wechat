import asyncio
import time

from openai import AsyncOpenAI

from xiaozhi_bridge.audio_utils import AudioUtils
from xiaozhi_bridge.config import BridgeConfig
from xiaozhi_bridge.tts_engine import TTSEngine


async def main():
    config = BridgeConfig.from_env()
    client = AsyncOpenAI(base_url=config.lm_studio_url, api_key=config.lm_studio_api_key)
    models = await client.models.list()
    print(f"LM Studio reachable, models={len(models.data)}")

    response = await client.chat.completions.create(
        model=config.model_name,
        messages=[
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": "Ban ten la gi?"},
        ],
        temperature=0.4,
    )
    reply = str(response.choices[0].message.content or "").strip()
    print(f"LLM ok, model={config.model_name}, reply={reply[:120]}")

    tts = TTSEngine(config)
    audio_utils = AudioUtils(config.ffmpeg_path)
    started_at = time.perf_counter()
    first_packet_ms = None
    packet_count = 0

    async for _packet in audio_utils.stream_mp3_to_opus_packets(
        tts.stream_audio("Xin chao, day la bai kiem tra giong noi.")
    ):
        packet_count += 1
        if first_packet_ms is None:
            first_packet_ms = (time.perf_counter() - started_at) * 1000.0

    print(
        "Streaming TTS ok, "
        f"first_packet_ms={first_packet_ms:.1f}, packets={packet_count}, model={config.tts_voice}"
    )


if __name__ == "__main__":
    asyncio.run(main())
