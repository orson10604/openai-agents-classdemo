import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

print("=== 測試環境變數 ===")
BASE_URL = os.getenv("EXAMPLE_BASE_URL") or ""
print(f"BASE_URL: '{BASE_URL}'")

API_KEY = os.getenv("EXAMPLE_API_KEY") or ""
print(f"API_KEY: '{API_KEY}'")

MODEL_NAME = os.getenv("EXAMPLE_MODEL_NAME") or ""
print(f"MODEL_NAME: '{MODEL_NAME}'")

print("\n=== 檢查是否為空值 ===")
print(f"BASE_URL 是否為空: {not BASE_URL}")
print(f"API_KEY 是否為空: {not API_KEY}")
print(f"MODEL_NAME 是否為空: {not MODEL_NAME}")

print(f"\n=== 從 .env 檔案讀取的所有環境變數 ===")
# 直接從 .env 檔案讀取
with open('.env', 'r') as f:
    content = f.read()
    print(content)
