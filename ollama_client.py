"""AI 对话客户端：Ollama + OpenAI Compatible API"""

import json
import requests


class AIClient:
    """统一 AI 客户端，支持 Ollama 和 OpenAI Compatible API"""

    def __init__(self, provider="ollama", base_url="http://localhost:11434",
                 model="qwen2.5:7b", api_key="", temperature=0.7):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

    def chat(self, messages, timeout=60):
        if self.provider == "ollama":
            return self._chat_ollama(messages, timeout)
        else:
            return self._chat_openai(messages, timeout)

    def _chat_ollama(self, messages, timeout):
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except requests.ConnectionError:
            raise ConnectionError("无法连接到 Ollama 服务")
        except requests.Timeout:
            raise TimeoutError("Ollama 响应超时")
        except Exception as e:
            raise RuntimeError(f"对话失败: {e}")

    def _chat_openai(self, messages, timeout):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        url = f"{self.base_url}/v1/chat/completions"
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.ConnectionError:
            raise ConnectionError("无法连接到 API 服务")
        except requests.Timeout:
            raise TimeoutError("API 响应超时")
        except Exception as e:
            raise RuntimeError(f"对话失败: {e}")


# 向后兼容别名
class OllamaClient(AIClient):
    """保留旧接口兼容"""
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        super().__init__(provider="ollama", base_url=base_url, model=model)
