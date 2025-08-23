#vibration agent

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, handoff, Runner
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# 重用既有的連線參數與方法
from upload_data import get_engine, MYSQL_DB, MYSQL_TABLE

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

#SQL connectation inf
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')
MYSQL_TABLE = os.getenv('MYSQL_TABLE')

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


CUSTOM_MODEL_PROVIDER = CustomModelProvider()

# 已註冊的 FUNCTION TOOLS:
# 1. get_weather(city: str)
# 2. get_vibration_all_on_date(date_str: str)
# 3. find_vibration_outliers_on_date(date_str: str, threshold: float = 3.0)
# 4. analyze_vibration_list(values: list[float]) -> dict
# 5. get_vibration_max_on_date(date_str: str)
# 6. calculate_sum(values: list[float]) -> float
# 7. get_current_time()

@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather tool for {city}")
    return f"The weather in {city} is sunny."

@function_tool
def get_vibration_all_on_date(date_str: str):
    print(f"[debug] getting all vibration data for date: {date_str}")
    import mysql.connector

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor()
        # Get column names
        cursor.execute(f"SHOW COLUMNS FROM {MYSQL_TABLE}")
        columns = [row[0] for row in cursor.fetchall()]
        vibration_col = next((col for col in columns if 'vibration' in col.lower()), None)
        time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        if not vibration_col:
            return "No vibration column found."
        if not time_columns:
            return "No time/date columns found for filtering."
        time_col = time_columns[0]
        query = (
            f"SELECT `{time_col}`, `{vibration_col}` "
            f"FROM `{MYSQL_TABLE}` "
            f"WHERE DATE(`{time_col}`) = %s "
            f"ORDER BY `{time_col}` ASC"
        )
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        if rows:
            result = [f"{time_col}: {row[0]}, {vibration_col}: {row[1]}" for row in rows]
            return "\n".join(result)
        else:
            return f"{date_str} 沒有資料。"
    except Exception as e:
        return f"Error retrieving vibration data: {e}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@function_tool
def find_vibration_outliers_on_date(date_str: str, threshold: float = 3.0):
    """
    取得指定日期的VIBRATION資料，找出離群值，並回傳該離群值的設備、對應時間點及其他欄位數據。
    threshold: 標準差倍數，預設3.0
    """
    print(f"[debug] finding vibration outliers for date: {date_str} with threshold {threshold}")
    import mysql.connector

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor(dictionary=True)
        # Get column names
        cursor.execute(f"SHOW COLUMNS FROM {MYSQL_TABLE}")
        columns = [row["Field"] for row in cursor.fetchall()]
        vibration_col = next((col for col in columns if 'vibration' in col.lower()), None)
        time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        if not vibration_col:
            return "No vibration column found."
        if not time_columns:
            return "No time/date columns found for filtering."
        time_col = time_columns[0]
        # 取得所有資料
        query = (
            f"SELECT * FROM `{MYSQL_TABLE}` "
            f"WHERE DATE(`{time_col}`) = %s"
        )
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        if not rows:
            return f"{date_str} 沒有資料。"
        values = [row[vibration_col] for row in rows if isinstance(row[vibration_col], (int, float))]
        if not values:
            return "No valid vibration data found."
        avg = sum(values) / len(values)
        std = (sum((x - avg) ** 2 for x in values) / len(values)) ** 0.5
        outliers = []
        for row in rows:
            val = row[vibration_col]
            if isinstance(val, (int, float)) and std > 0 and abs(val - avg) > threshold * std:
                outlier_info = {col: row[col] for col in columns}
                outliers.append(outlier_info)
        if not outliers:
            return f"{date_str} 沒有發現離群值。"
        result = "離群值資料如下：\n"
        for idx, outlier in enumerate(outliers, 1):
            info = ", ".join(f"{k}: {v}" for k, v in outlier.items())
            result += f"{idx}. {info}\n"
        return result.strip()
    except Exception as e:
        return f"Error finding vibration outliers: {e}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@function_tool
def analyze_vibration_list(values: list[float]) -> dict:
    print(f"[debug] analyzing vibration list: {values}")
    if not values:
        return {"error": "Input list is empty."}
    n = len(values)
    avg = sum(values) / n
    var = sum((x - avg) ** 2 for x in values) / n
    max_val = max(values)
    min_val = min(values)
    return {
        "平均值": avg,
        "變異數": var,
        "最大值": max_val,
        "最小值": min_val
    }

@function_tool
def get_vibration_max_on_date(date_str: str):
    print(f"[debug] getting max vibration data for date: {date_str}")
    import mysql.connector

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor()
        # Get column names
        cursor.execute(f"SHOW COLUMNS FROM {MYSQL_TABLE}")
        columns = [row[0] for row in cursor.fetchall()]
        vibration_col = next((col for col in columns if 'vibration' in col.lower()), None)
        # Find possible time/date columns
        time_columns = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        if not vibration_col:
            return "No vibration column found."
        if not time_columns:
            return "No time/date columns found for filtering."
        time_col = time_columns[0]
        query = (
            f"SELECT `{time_col}`, `{vibration_col}` "
            f"FROM `{MYSQL_TABLE}` "
            f"WHERE DATE(`{time_col}`) = %s "
            f"ORDER BY `{vibration_col}` DESC "
            f"LIMIT 1"
        )
        cursor.execute(query, (date_str,))
        row = cursor.fetchone()
        if row:
            return f"在 {date_str}，最大 {vibration_col} 為 {row[1]}，發生於 {time_col}: {row[0]}"
        else:
            return f"{date_str} 沒有資料。"
    except Exception as e:
        return f"Error retrieving vibration data: {e}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@function_tool
def calculate_sum(values: list[float]) -> float:
    print(f"[debug] calculating sum for: {values}")
    return sum(values)

@function_tool
def get_current_time():
    print("[debug] getting current time")
    return f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

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


# 已註冊的 FUNCTION TOOLS:
# 1. get_weather(city: str)
# 2. get_vibration_all_on_date(date_str: str)
# 3. find_vibration_outliers_on_date(date_str: str, threshold: float = 3.0)
# 4. analyze_vibration_list(values: list[float]) -> dict
# 5. get_vibration_max_on_date(date_str: str)
# 6. calculate_sum(values: list[float]) -> float
# 7. get_current_time()

async def main():

    Web_agent = Agent(name="Information person",
                        instructions = """你是一個資訊人員，
                        可以用對應的tools來查詢現在時間，天氣和電影資訊。
                        """,
                        tools=[get_current_time,get_weather,google_search]
                    )

    Vib_agent = Agent(name="Vibration engineer", 
                  instructions="""You only respond in 繁體中文. 
                  你是一個設備維護工程師，可以用對應的tools來查SQL資料庫(得出的資料要取abs)，
                  並提供設備的振動數據分析與維護建議和故障排除步驟。
                  大致流程為: [取得資料]->[分析資料]->[解析資料]
                  根據使用者的目的來挑選，那目前可選用的為:

                  [取得資料]: get_vibration_all_on_date, get_vibration_max_on_date
                  [分析資料]: analyze_vibration_list, calculate_sum
                  [解析資料]: find_vibration_outliers_on_date

                  請繁體中文輸出
                  """, 
                  tools=[get_vibration_all_on_date, 
                            get_vibration_max_on_date, 
                            analyze_vibration_list, 
                            calculate_sum, 
                            find_vibration_outliers_on_date])

    triage_agent = Agent(name="triage person",
                        instructions = """
                        你是一個分配任務的人員，
                        你的工作是根據使用者的需求，將使用者導向適合的agent來處理。
                        使用者有時會同時有多個需求，請根據使用者的需求請依序來分配適合的agent。
                        例如，使用者想查詢天氣或電影資訊，則導向資訊人員(Web_agent)；
                        如果使用者想查詢設備的振動數據，則導向振動工程師(Vib_agent),而不是google search。
                        最後請繁體中文輸出
                        """,
                        handoffs=[Vib_agent, handoff(Web_agent)]
    )

    result = Runner.run_streamed(triage_agent, 
                                input="幫我查2025/7/30的振動資料分析" ,#"台中天氣如何? 請幫我查詢電影時刻，我想看電影",
                                run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER))
    
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())