import edge_tts


class TTSEngine:
    def __init__(self, config):
        self.voice = config.tts_voice

    async def generate_audio(self, text, output_file):
        """
        Generate TTS audio and save to output_file.
        """
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)

    async def stream_audio(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        async for message in communicate.stream():
            if message.get("type") == "audio":
                yield message["data"]
