from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner
from agents.mcp import MCPServer, MCPServerSse
from agents.model_settings import ModelSettings


# 載入 .env 檔案
load_dotenv()

from agents import (
    Agent,
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    function_tool,
    set_tracing_disabled,
)

BASE_URL = os.getenv("EXAMPLE_BASE_URL") or ""
print(BASE_URL)
API_KEY = os.getenv("EXAMPLE_API_KEY") or ""
MODEL_NAME = os.getenv("EXAMPLE_MODEL_NAME") or ""

if not BASE_URL or not API_KEY or not MODEL_NAME:
    raise ValueError(
        "Please set EXAMPLE_BASE_URL, EXAMPLE_API_KEY, EXAMPLE_MODEL_NAME via env var or code."
    )


"""This example uses a custom provider for some calls to Runner.run(), and direct calls to OpenAI for
others. Steps:
1. Create a custom OpenAI client.
2. Create a ModelProvider that uses the custom client.
3. Use the ModelProvider in calls to Runner.run(), only when we want to use the custom LLM provider.

Note that in this example, we disable tracing under the assumption that you don't have an API key
from platform.openai.com. If you do have one, you can either set the `OPENAI_API_KEY` env var
or call set_tracing_export_api_key() to set a tracing specific key.
"""
client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(disabled=True)


class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(model=model_name or MODEL_NAME, openai_client=client)

prompt="""如果使用者有問題，請使用rag這個mcptool查相關資訊，輸入資料如下：
        name="ragflow_retrieval", 
        arguments={"dataset_ids": ["13b1501074d311f089b70242ac180007"], 
                   "document_ids": ["654bc63a74d311f0a1080242ac180007"]
"""

CUSTOM_MODEL_PROVIDER = CustomModelProvider()


@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather tool for {city}")
    return f"The weather in {city} is sunny."

@function_tool
def google_search(query: str):
    print(f"[debug] performing Google search for: {query}")
    return f"Search results for '{query}' are not available in this example."


async def mcp_open():
    async with MCPServerSse(
        name="RAGflow Server",
        params={
            "url": "http://localhost:7056/sse",
        },
    ) as server:
        await main_agent(server)


async def main_agent(mcp_server: MCPServer):


    agent = Agent(name="Assistant", 
                  instructions=f"""You only respond in 繁體中文. 
                                你可以使用的mcp工具為：{prompt} ，
                                請先分析關鍵字後，輸入關鍵字來使用工具

""", 
                  mcp_servers=[mcp_server],
                  tools=[get_weather, google_search])

    # This will use the custom model provider
    # result = await Runner.run(
    #     agent,
    #     "台北天氣如何?",
    #     run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
    # )
    # print(result.final_output)
    result = Runner.run_streamed(agent, 
                                input="請問冷氣的型號？ 也介紹詳細",
                                run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER))
    
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)

    # If you uncomment this, it will use OpenAI directly, not the custom provider
    # result = await Runner.run(
    #     agent,
    #     "What's the weather in Tokyo?",
    # )
    # print(result.final_output)


if __name__ == "__main__":
    process: subprocess.Popen[Any] | None = None
    try:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        server_file = os.path.join(this_dir, "mcp_server.py")

        print("Starting Simple Prompt Server...")
        process = subprocess.Popen(["python", server_file])
        time.sleep(3)
        print("Server started\n")
    except Exception as e:
        print(f"Error starting server: {e}")
        exit(1)

    try:
        asyncio.run(mcp_open())
    finally:
        if process:
            process.terminate()
            print("Server terminated.")
    