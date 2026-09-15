import os

from dotenv import load_dotenv
from openai import OpenAI


class LLMClient:
    """Client for the company's OpenAI-compatible AI endpoint."""

    def __init__(self):
        load_dotenv()

        api_key = os.getenv("API_KEY")
        base_url = os.getenv("BASE_URL")
        model = os.getenv("MODEL")

        if not api_key:
            raise ValueError("API_KEY is missing from .env")

        if not base_url:
            raise ValueError("BASE_URL is missing from .env")

        if not model:
            raise ValueError("MODEL is missing from .env")

        self.model = model.strip()
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/")
        )

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("LLM returned an empty response")

        return content
