import time

from openai import OpenAI

from common import BaseLLM, error, logger
from .model_router import get_model_route
from .prompt_loader import build_role_prompt
from .prompts import LLM_ACTION_PROMPT


MEMORY_EXTRACTION_PROMPT = """
You extract safe long-term memories for an emotional companion robot.
Return JSON only, no markdown.

Schema:
{
  "memories": [
    {
      "memory_type": "preference|identity|relationship|habit|interaction_style|reminder",
      "content": "short Chinese memory sentence",
      "confidence": 0.0-1.0,
      "reason": "why it should be remembered"
    }
  ]
}

Rules:
- Save only stable user preferences, identity, important relationships, habits, reminders, or interaction style.
- Do not save secrets, passwords, API keys, ID numbers, bank cards, exact addresses, precise location, medical diagnoses, illegal details, or crisis/self-harm content.
- If nothing safe and useful should be remembered, return {"memories":[]}.
"""


class GPT(BaseLLM):
    def __init__(self):
        super().__init__("GPT")
        self.json_path = "gpt_api.json"
        self._create_empty_json()
        self.default_route = get_model_route("fast_chat")
        self.default_chat_model = self.default_route.model
        self.default_chat_timeout = self.default_route.timeout_seconds

    def connect(self, api_url="", api_key=""):
        if not api_url or not api_key:
            api_url, api_key = self.read_json()
        self.api_url = api_url
        self.api_key = api_key
        try:
            self.client = OpenAI(
                base_url=self.api_url,
                api_key=self.api_key,
                timeout=self.default_chat_timeout,
            )
            self.client.models.list()
            logger.info("Connect to LLM API Success!")
            return True
        except Exception as e:
            error(e, "Connect to LLM API Failed! Please check the API configuration")
            return False

    def chat(
        self,
        message="",
        model=None,
        temperature=None,
        max_tokens=None,
        timeout=None,
        route_name="fast_chat",
        extra_context=None,
    ):
        route = get_model_route(route_name)
        model = model or route.model
        temperature = route.temperature if temperature is None else temperature
        max_tokens = max_tokens or route.max_tokens
        timeout = timeout or route.timeout_seconds
        messages = [
            {"role": "system", "content": build_role_prompt(extra_context=extra_context)},
            {"role": "user", "content": LLM_ACTION_PROMPT + message},
        ]
        start_time = time.perf_counter()
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            extra_body={"enable_thinking": route.enable_thinking},
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = getattr(response, "usage", None)
        logger.info(
            "LLM route=%s model=%s latency_ms=%s prompt_tokens=%s completion_tokens=%s",
            route.name,
            model,
            latency_ms,
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
        )
        return response.choices[0].message.content.strip()

    def speech(self, model="qwen3-asr-flash", audio_path=""):
        audio_file = open(audio_path, "rb")
        transcription = self.client.audio.transcriptions.create(
            model=model,
            file=audio_file,
        )
        return transcription.text

    def speak(self, text="", model="tts-1", voice="onyx", audio_path=""):
        response = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
        )
        logger.info(f"Voice: {voice}")
        response.stream_to_file(audio_path)

    def extract_memories(self, user_text):
        route = get_model_route("fallback_or_rag")
        response = self.client.chat.completions.create(
            model=route.model,
            messages=[
                {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
                {"role": "user", "content": str(user_text or "")},
            ],
            temperature=0,
            max_tokens=300,
            timeout=route.timeout_seconds,
            extra_body={"enable_thinking": route.enable_thinking},
        )
        return response.choices[0].message.content.strip()
