from __future__ import annotations

import os
import httpx


class ModelGateway:
    """Connect to local Ollama or OpenAI-style APIs with graceful fallback."""

    def __init__(self) -> None:
        self.backend = os.getenv("LLM_BACKEND", "none").lower()
        self.timeout = float(os.getenv("LLM_TIMEOUT", "30"))

    def generate(self, question: str, profile: dict, grounded_answer: str) -> str:
        if self.backend in ("", "none"):
            return grounded_answer

        prompt = self._build_prompt(question, profile, grounded_answer)
        try:
            if self.backend == "ollama":
                return self._call_ollama(prompt)
            if self.backend == "openai":
                return self._call_openai(prompt)
            return grounded_answer
        except Exception:
            return grounded_answer

    def _build_prompt(self, question: str, profile: dict, grounded_answer: str) -> str:
        return (
            "你是环保咨询助手。必须保留引用可追溯与风险边界，不得输出法律裁决。\n"
            f"用户问题: {question}\n"
            f"企业画像: {profile}\n"
            "请基于下述检索答案进行润色，保持结构不变并避免新增无依据条款:\n"
            f"{grounded_answer}"
        )

    def _call_ollama(self, prompt: str) -> str:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        url = f"{base_url.rstrip('/')}/api/generate"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json={"model": model, "prompt": prompt, "stream": False})
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", "").strip() or ""

    def _call_openai(self, prompt: str) -> str:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing")

        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是环保咨询助手，必须保持引用和风险边界。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"].strip()
