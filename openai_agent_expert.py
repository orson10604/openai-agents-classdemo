from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner
from datetime import datetime


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

BASE_URL = "http://140.134.174.70:11434/v1"
my_server_url="http://140.134.60.218:11425/v1"
print(BASE_URL)
API_KEY = os.getenv("EXAMPLE_API_KEY") or ""
MODEL_NAME_1 = "qwen3:0.6b"
MODEL_NAME_1 = "gpt-oss:20b"
MODEL_NAME_2 = "gemma3_code_model"

if not BASE_URL or not API_KEY or not MODEL_NAME_1 or not MODEL_NAME_2:
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
client2 = AsyncOpenAI(base_url=my_server_url, api_key=API_KEY)
set_tracing_disabled(disabled=True)


@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather tool for {city}")
    return f"The weather in {city} is sunny."

@function_tool
def google_search(query: str):
    print(f"[debug] performing Google search for: {query}")
    from googlesearch import search #import library


    results = search(query, advanced=True) #執行程式

    answer=""
    url=""
    for result in results: #顯示
        answer += ", " + result.description
        url += ", " + result.url
        
    return f"Search results for '{query}' , information are :{answer} and corresponding to {url}"


@function_tool
def calculate_sum(values: list[float]) -> float:
    print(f"[debug] calculating sum for: {values}")
    return sum(values)

@function_tool
def get_current_time():
    print("[debug] getting current time")
    return f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


async def main():
    alarm_agent = Agent(name="Assistant",
                                model=OpenAIChatCompletionsModel(model=MODEL_NAME_2, openai_client=client)) 
                 # tools=[get_weather, get_current_time, google_search, calculate_sum])

    entrance_agent = Agent(name="triage person",
                        instructions = """
                        你是一個分配任務的人員，
                        你的工作是根據使用者的需求，將使用者導向適合的agent來處理。
                        如果有提到類似ERROR_UNEXPECTED_MM_MAP_ERROR	557 (0x22D) 或 ERROR_INVALID_PRINTER_COMMAND	1803 (0x70B) 以上為舉例
                        則呼叫alarm_agent. 如果無關，就直接回覆使用者的問題。
                        """,
                        model=OpenAIChatCompletionsModel(model=MODEL_NAME_1, openai_client=client2),
                        tools=[get_weather, get_current_time, google_search, calculate_sum],
                        handoffs=[alarm_agent]
                        )

    result = Runner.run_streamed(entrance_agent, 
                                input="brad pitt有什麼新電影，台中上映的場次?")#"ERROR_INVALID_PRINTER_COMMAND	1803 (0x70B)")
                                #"brad pitt有什麼新電影，台中上映的場次?" ,#"台中天氣如何? 請幫我查詢電影時刻，我想看電影",)
    
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
    asyncio.run(main())