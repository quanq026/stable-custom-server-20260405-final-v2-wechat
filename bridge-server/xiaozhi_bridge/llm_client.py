import time
from dataclasses import dataclass, field

from openai import AsyncOpenAI


@dataclass
class ConversationState:
    device_id: str
    system_prompt: str
    summary: str = ""
    tail_messages: list = field(default_factory=list)
    last_user_text: str = ""
    last_assistant_text: str = ""
    last_activity_at: float = 0.0
    current_session_id: str = ""


class LLMClient:
    def __init__(self, config):
        self.client = AsyncOpenAI(base_url=config.lm_studio_url, api_key=config.lm_studio_api_key)
        self.model_name = config.model_name
        self.system_prompt = config.system_prompt
        self.context_tail_messages = config.context_tail_messages
        self.session_summary_max_chars = config.session_summary_max_chars
        self.conversation_idle_timeout_seconds = config.conversation_idle_timeout_seconds
        self.conversations = {}
        self.active_sessions = {}
        self.sessions = self.conversations

    def _conversation_key(self, session_id, device_id=None):
        return str(device_id or session_id)

    def start_session(self, session_id, device_id=None):
        conversation_key = self._conversation_key(session_id, device_id)
        state = self.conversations.get(conversation_key)
        if state is None:
            state = ConversationState(device_id=conversation_key, system_prompt=self.system_prompt)
            self.conversations[conversation_key] = state
        state.current_session_id = session_id
        self.active_sessions[session_id] = conversation_key
        return state

    def end_session(self, session_id):
        conversation_key = self.active_sessions.pop(session_id, None)
        if not conversation_key:
            return
        state = self.conversations.get(conversation_key)
        if state and state.current_session_id == session_id:
            state.current_session_id = ""

    def _get_state(self, session_id):
        conversation_key = self.active_sessions.get(session_id)
        if conversation_key:
            state = self.conversations.get(conversation_key)
            if state is not None:
                return state
            return self.start_session(session_id, device_id=conversation_key)
        return self.start_session(session_id)

    def cleanup_expired_conversations(self, now=None):
        current_time = time.monotonic() if now is None else now
        expired = []
        for conversation_key, state in self.conversations.items():
            if state.last_activity_at <= 0:
                continue
            if current_time - state.last_activity_at > self.conversation_idle_timeout_seconds:
                expired.append(conversation_key)

        for conversation_key in expired:
            self.conversations.pop(conversation_key, None)

    def _append_summary(self, state, overflow_messages):
        parts = []
        for message in overflow_messages:
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            parts.append(f"{message.get('role', 'user')}: {content}")
        if not parts:
            return

        merged = " | ".join(parts)
        if state.summary:
            merged = f"{state.summary} | {merged}"
        state.summary = merged[-self.session_summary_max_chars :]

    def _append_message(self, session_id, role, text):
        clean_text = str(text).strip()
        if not clean_text:
            return

        state = self._get_state(session_id)
        state.tail_messages.append({"role": role, "content": clean_text})
        if role == "user":
            state.last_user_text = clean_text
        elif role == "assistant":
            state.last_assistant_text = clean_text
        state.last_activity_at = time.monotonic()

        overflow_count = len(state.tail_messages) - self.context_tail_messages
        if overflow_count > 0:
            overflow_messages = state.tail_messages[:overflow_count]
            state.tail_messages = state.tail_messages[overflow_count:]
            self._append_summary(state, overflow_messages)

    def append_user_message(self, session_id, text):
        self._append_message(session_id, "user", text)

    def append_assistant_message(self, session_id, text):
        self._append_message(session_id, "assistant", text)

    def build_messages(self, session_id):
        self.cleanup_expired_conversations()
        state = self._get_state(session_id)
        messages = [{"role": "system", "content": state.system_prompt}]
        if state.summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"Tom tat boi canh session hien tai: {state.summary}",
                }
            )
        messages.extend(state.tail_messages)
        return messages

    async def get_response(self, session_id, user_text):
        self.cleanup_expired_conversations()
        self.append_user_message(session_id, user_text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=self.build_messages(session_id),
                temperature=0.4,
            )
            reply = str(response.choices[0].message.content or "").strip()
            if reply:
                self.append_assistant_message(session_id, reply)
            return reply
        except Exception as exc:
            print(f"Error getting response from LLM: {exc}", flush=True)
            return "Xin loi, toi dang gap truc trac khi tra loi."
