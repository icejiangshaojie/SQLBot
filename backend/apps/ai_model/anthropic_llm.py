"""Anthropic-compatible LLM for ZA DeepSeek (uses Anthropic Messages API with httpx)"""
from typing import Any, Optional, Iterator
import json
import httpx
from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.language_models import LanguageModelInput
from langchain_core.runnables import RunnableConfig


class ChatAnthropicCompat(BaseChatModel):
    """Anthropic Messages API compatible chat model (no SSL verify for internal CA)"""

    model: str = "deepseek-v4-flash"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    stream_usage: bool = True

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        # Convert messages to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_msg = msg.content
            elif isinstance(msg, HumanMessage):
                anthropic_messages.append({"role": "user", "content": msg.content})
            else:
                anthropic_messages.append({"role": "assistant", "content": msg.content})

        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": anthropic_messages,
            "temperature": self.temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        with httpx.Client(verify=False, timeout=120) as client:
            resp = client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract text from response
        text_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])

        content = "".join(text_parts)
        ai_msg = AIMessage(content=content)
        usage = data.get("usage", {})
        if usage:
            ai_msg.usage_metadata = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            }

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    @property
    def _llm_type(self) -> str:
        return "anthropic_compat"

    def stream(self, input: LanguageModelInput, config: Optional[RunnableConfig] = None, *,
               stop=None, **kwargs):
        """Yield streaming chunks via Anthropic SSE"""
        messages = self._convert_input(input).to_messages()
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_msg = msg.content
            elif isinstance(msg, HumanMessage):
                anthropic_messages.append({"role": "user", "content": msg.content})
            else:
                anthropic_messages.append({"role": "assistant", "content": msg.content})

        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": anthropic_messages,
            "temperature": self.temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        _input_tokens = 0
        _output_tokens = 0

        with httpx.Client(verify=False, timeout=120) as client:
            with client.stream("POST", f"{self.base_url}/v1/messages", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            evt_type = data.get("type", "")

                            if evt_type == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield AIMessageChunk(content=delta["text"])

                            elif evt_type == "message_delta":
                                # message_delta 包含最终的 token usage
                                # 注意：ZA DeepSeek 代理在 message_delta 中返回 input_tokens，
                                # 而 message_start 中的 input_tokens 始终为 0
                                delta_usage = data.get("usage", {})
                                if delta_usage.get("input_tokens"):
                                    _input_tokens = delta_usage["input_tokens"]
                                if delta_usage.get("output_tokens"):
                                    _output_tokens = delta_usage["output_tokens"]

                        except json.JSONDecodeError:
                            pass

        # 发送一个带 usage_metadata 的最终 chunk，让 get_token_usage 能捕获
        final_chunk = AIMessageChunk(content="")
        final_chunk.usage_metadata = {
            "input_tokens": _input_tokens,
            "output_tokens": _output_tokens,
            "total_tokens": _input_tokens + _output_tokens,
        }
        print(f"[AI2BI-DEBUG] Anthropic stream done: input_tokens={_input_tokens}, output_tokens={_output_tokens}, total={_input_tokens + _output_tokens}", flush=True)
        yield final_chunk
