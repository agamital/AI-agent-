import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Message:
    role: str
    content: str


# Shared usage tracker — updated after every call, read by the UI
USAGE = {
    "groq":   {"limit_tokens": None, "remaining_tokens": None,
               "limit_requests": None, "remaining_requests": None, "reset": None,
               "daily_limit": None, "daily_used": None, "daily_remaining": None, "daily_reset": None},
    "gemini": {"used_requests": 0, "limit_requests": None},
}

# Set to a human message when ALL providers are rate-limited
LAST_ERROR = {"rate_limited": False, "message": "", "retry_after": ""}


class _Provider:
    name = "base"
    MAX_RETRIES = 3

    def chat(self, messages, temperature=0.3, max_tokens=1024):
        delays = [1.0, 2.0, 4.0]
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._call(messages, temperature, max_tokens)
            except Exception as exc:
                err = str(exc).lower()
                is_rate = "rate" in err or "429" in err or "quota" in err
                is_transient = is_rate or any(k in err for k in ("503", "timeout", "connection"))
                if is_rate:
                    import re as _re
                    msg = str(exc)
                    m = _re.search(r"try again in ([\d.]+m?[\d.]*s)", msg)
                    LAST_ERROR["rate_limited"] = True
                    LAST_ERROR["retry_after"] = m.group(1) if m else ""
                    # Parse daily quota from the error message itself
                    lim = _re.search(r"Limit (\d+)", msg)
                    used = _re.search(r"Used (\d+)", msg)
                    if lim and used and self.name == "groq":
                        limit_v = int(lim.group(1))
                        used_v = int(used.group(1))
                        USAGE["groq"]["daily_limit"] = limit_v
                        USAGE["groq"]["daily_used"] = used_v
                        USAGE["groq"]["daily_remaining"] = max(0, limit_v - used_v)
                        USAGE["groq"]["daily_reset"] = m.group(1) if m else ""
                if is_transient and attempt < self.MAX_RETRIES - 1:
                    time.sleep(delays[attempt])
                else:
                    logger.error("[%s] call failed: %s", self.name, exc)
                    return None
        return None

    def _call(self, messages, temperature, max_tokens=1024):
        raise NotImplementedError


class _GroqProvider(_Provider):
    name = "groq"
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key):
        from groq import Groq
        self._client = Groq(api_key=api_key)

    def _call(self, messages, temperature, max_tokens=1024):
        # Use raw response to access rate-limit headers
        raw = self._client.chat.completions.with_raw_response.create(
            model=self.MODEL,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Capture rate-limit headers
        h = raw.headers
        try:
            USAGE["groq"]["limit_tokens"] = _to_int(h.get("x-ratelimit-limit-tokens"))
            USAGE["groq"]["remaining_tokens"] = _to_int(h.get("x-ratelimit-remaining-tokens"))
            USAGE["groq"]["limit_requests"] = _to_int(h.get("x-ratelimit-limit-requests"))
            USAGE["groq"]["remaining_requests"] = _to_int(h.get("x-ratelimit-remaining-requests"))
            USAGE["groq"]["reset"] = h.get("x-ratelimit-reset-tokens")
        except Exception:
            pass

        completion = raw.parse()
        return completion.choices[0].message.content


class _GeminiProvider(_Provider):
    name = "gemini"
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai

    def _call(self, messages, temperature, max_tokens=1024):
        system_parts = [m.content for m in messages if m.role == "system"]
        history = [m for m in messages if m.role != "system"]
        system_instruction = "\n\n".join(system_parts) if system_parts else None
        model = self._genai.GenerativeModel(
            model_name=self.MODEL,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
        )
        gemini_history = []
        for m in history[:-1]:
            role = "user" if m.role == "user" else "model"
            gemini_history.append({"role": role, "parts": [m.content]})
        chat = model.start_chat(history=gemini_history)
        last_msg = history[-1].content if history else ""
        response = chat.send_message(last_msg)
        # Gemini doesn't expose remaining quota in headers — track request count
        USAGE["gemini"]["used_requests"] += 1
        return response.text


def _to_int(val):
    """Parse Groq header values like '100000' or '95k' into int."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


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

    def chat(self, messages, temperature=0.3, max_tokens=1024):
        LAST_ERROR["rate_limited"] = False
        for provider in self._providers:
            result = provider.chat(messages, temperature, max_tokens)
            if result is not None:
                LAST_ERROR["rate_limited"] = False
                return result
        # All providers failed
        if LAST_ERROR["rate_limited"]:
            retry = LAST_ERROR.get("retry_after", "")
            LAST_ERROR["message"] = (
                f"נגמרה מכסת ה-API הזמנית" +
                (f" — נסה שוב בעוד {retry}" if retry else " — נסה שוב בעוד מספר דקות") + "."
            )
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
