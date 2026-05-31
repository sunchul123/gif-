"""AI 对话客户端：Ollama + OpenAI Compatible API"""

import json
import requests


class AIClient:
    """统一 AI 客户端，支持 Ollama 和 OpenAI Compatible API"""

    def __init__(self, provider="ollama", base_url="http://localhost:11434",
                 model="qwen2.5:7b", api_key="", temperature=0.7):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        # Ollama 原生 API 不需要 /v1 后缀，自动去掉
        if provider == "ollama" and self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3].rstrip("/")
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
        url = f"{self.base_url}/api/chat"
        
        # 添加请求日志
        print(f"[Ollama] 发送请求到: {url}")
        print(f"[Ollama] 模型: {self.model}")
        print(f"[Ollama] 消息数: {len(messages)}")
        
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            
            print(f"[Ollama] 响应状态码: {resp.status_code}")
            
            # 检查 HTTP 状态码
            if resp.status_code == 404:
                raise ConnectionError(
                    f"API 端点不存在: {url}\n"
                    f"请确认 Ollama 版本是否正确"
                )
            elif resp.status_code == 400:
                error_msg = resp.json().get("error", "未知错误")
                raise ConnectionError(
                    f"请求参数错误: {error_msg}\n"
                    f"请检查模型 '{self.model}' 是否正确"
                )
            
            resp.raise_for_status()
            result = resp.json().get("message", {}).get("content", "")
            print(f"[Ollama] 回复长度: {len(result)} 字符")
            return result
            
        except requests.ConnectionError as e:
            # 提供详细的诊断信息
            import socket
            from urllib.parse import urlparse
            
            try:
                parsed = urlparse(self.base_url)
                host = parsed.hostname or 'localhost'
                port = parsed.port or 11434
                
                # 测试端口连通性
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result != 0:
                    raise ConnectionError(
                        f"无法连接到 Ollama 服务 ({self.base_url})\n\n"
                        f"请检查:\n"
                        f"1. Ollama 是否已启动 (运行 'ollama serve')\n"
                        f"2. 端口 {port} 是否正确\n"
                        f"3. 防火墙是否阻止了连接"
                    )
                else:
                    # 端口可访问但请求失败
                    raise ConnectionError(
                        f"可以连接到 Ollama ({self.base_url})，但请求失败\n\n"
                        f"可能原因:\n"
                        f"1. 模型 '{self.model}' 未下载\n"
                        f"   解决: ollama pull {self.model}\n"
                        f"2. Ollama 服务异常\n"
                        f"   解决: 重启 Ollama 服务\n\n"
                        f"查看可用模型: ollama list"
                    )
            except ConnectionError:
                raise
            except Exception as diag_error:
                raise ConnectionError(f"无法连接到 Ollama 服务: {e}")
                
        except requests.Timeout:
            raise TimeoutError(
                f"Ollama 响应超时 (>{timeout}秒)\n"
                f"模型 '{self.model}' 可能需要更长时间加载，尝试增加超时时间"
            )
        except KeyError as e:
            raise RuntimeError(
                f"API 响应格式错误: {e}\n"
                f"请检查 Ollama 版本是否兼容"
            )
        except Exception as e:
            # 尝试从响应中获取错误信息
            try:
                if 'resp' in locals() and resp.text:
                    error_detail = resp.json().get("error", str(e))
                    raise RuntimeError(f"对话失败: {error_detail}")
            except:
                pass
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
