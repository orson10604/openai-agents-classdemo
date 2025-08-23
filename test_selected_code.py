import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 測試您選中的程式碼片段
BASE_URL = os.getenv("EXAMPLE_BASE_URL") or ""
print(BASE_URL)
API_KEY = os.getenv("EXAMPLE_API_KEY") or ""
MODEL_NAME = os.getenv("EXAMPLE_MODEL_NAME") or ""

print(f"BASE_URL: {BASE_URL}")
print(f"API_KEY: {API_KEY}")
print(f"MODEL_NAME: {MODEL_NAME}")

# 檢查是否會觸發 ValueError
if not BASE_URL or not API_KEY or not MODEL_NAME:
    print("❌ 會觸發 ValueError: 有環境變數為空")
else:
    print("✅ 所有環境變數都有值，不會觸發 ValueError")
