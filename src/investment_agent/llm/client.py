import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Message:
    role: str
    content: str

class _Provider:
    name = "base"
    MAX_RETRIES = 3

    def chat(self, messages, temperature=0.3):
        delays = [1.0, 2.0, 4.0]
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._call(messages, temperature)
            except Exception as exc:
                err = str(exc).lower()
                is_transient = any(k in err for k in ("rate", "429", "503", "timeout", "connection"))
                if is_transient and attempt < self.MAX_RETRIES - 1:
                    time.sleep(delays[attempt])
                else:
                    logger.error("[%s] call failed: %s", self.name, exc)
                    return None
        return None

    def _call(self, messages, temperature):
        raise NotImplementedError

class _GroqProvider(_Provider):
    name = "groq"
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key):
        from groq import Groq
        self._client = Groq(api_key=api_key)

    def _call(self, messages, temperature):
        response = self._client.chat.completions.create(
            model=self.MODEL,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=4096,
        )
        return response.choices[0].message.content

class _GeminiProvider(_Provider):
    name = "gemini"
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai

    def _call(self, messages, temperature):
        system_parts = [m.content for m in messages if m.role == "system"]
        history = [m for m in messages if m.role != "system"]
        system_instruction = "\n\n".join(system_parts) if system_parts else None
        model = self._genai.GenerativeModel(
            model_name=self.MODEL,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature, "max_output_tokens": 4096},
        )
        gemini_history = []
        for m in history[:-1]:
            role = "user" if m.role == "user" else "model"
            gemini_history.append({"role": role, "parts": [m.content]})
        chat = model.start_chat(history=gemini_history)
        last_msg = history[-1].content if history else ""
        response = chat.send_message(last_msg)
        return response.text

class LLMClient:
    def __init__(self, groq_api_key=None, gemini_api_key=None):
        groq_key = groq_api_key or os.getenv("GROQ_API_KEY")
        gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self._providers = []

        if groq_key:
            try:
                self._providers.append(_GroqProvider(groq_key))
                print("✅ Groq initialised")
            except Exception as exc:
                print(f"⚠️ Groq failed: {exc}")

        if gemini_key:
            try:
                self._providers.append(_GeminiProvider(gemini_key))
                print("✅ Gemini initialised")
            except Exception as exc:
                print(f"⚠️ Gemini failed: {exc}")

        if not self._providers:
            raise RuntimeError("No LLM provider available. Set GROQ_API_KEY and/or GEMINI_API_KEY.")

    def chat(self, messages, temperature=0.3):
        for provider in self._providers:
            result = provider.chat(messages, temperature)
            if result is not None:
                return result
        return None

    def chat_with_system(self, system_prompt, user_message, history=None, temperature=0.3):
        messages = [Message(role="system", content=system_prompt)]
        if history:
            messages.extend(history)
        messages.append(Message(role="user", content=user_message))
        return self.chat(messages, temperature)

    @property
    def active_provider(self):
        return self._providers[0].name if self._providers else "none"
