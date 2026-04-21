"""
本地 Ollama 调用封装工具。

支持调用本地 Ollama 模型（如 qwen2.5:3b）进行结构化抽取、报告生成等任务。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """本地 Ollama API 客户端封装。"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        timeout: int = 120,
    ) -> None:
        """
        初始化 Ollama 客户端。

        Args:
            base_url: Ollama 服务地址
            model: 使用的模型名称（固定为 qwen2.5:3b，已通过对比测试验证）
            timeout: 请求超时时间（秒）
        
        注意：本项目使用 qwen2.5:3b 模型，相比之前的模型速度提升1.6倍，质量相同。
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        调用 Ollama 生成文本。

        Args:
            prompt: 用户提示词
            model: 模型名称（可选，默认使用初始化时的模型）
            system: 系统提示词（可选）
            temperature: 温度参数
            max_tokens: 最大生成token数（可选）

        Returns:
            生成的文本内容
        """
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 调用失败: {e}")
            raise RuntimeError(f"Ollama 调用失败: {e}") from e

    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        调用 Ollama 生成 JSON 格式输出。

        Args:
            prompt: 用户提示词
            model: 模型名称（可选）
            system: 系统提示词（可选）
            temperature: 温度参数（JSON模式建议较低）
            max_tokens: 最大生成token数（可选）

        Returns:
            解析后的 JSON 对象
        """
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "").strip()

            if not response_text:
                logger.warning("Ollama 返回空响应")
                return {}

            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 原始响应: {response_text}")
            raise RuntimeError(f"JSON 解析失败: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 调用失败: {e}")
            raise RuntimeError(f"Ollama 调用失败: {e}") from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        使用对话接口调用 Ollama。

        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称（可选）
            temperature: 温度参数
            max_tokens: 最大生成token数（可选）

        Returns:
            生成的文本内容
        """
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            message = result.get("message", {})
            return message.get("content", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama 对话调用失败: {e}")
            raise RuntimeError(f"Ollama 对话调用失败: {e}") from e

    def health_check(self) -> bool:
        """
        检查 Ollama 服务是否可用。

        Returns:
            服务是否可用
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
