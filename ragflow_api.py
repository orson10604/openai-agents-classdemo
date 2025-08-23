from openai import OpenAI
from dotenv import load_dotenv
import os

# 載入 .env 檔案
load_dotenv()

model = "model"
ragflow_api_key = os.getenv("ragflow_api_key") 
ragflow_address =os.getenv("ragflow_address")
chat_id=os.getenv("chat_id")

from ragflow_sdk import RAGFlow

rag_object = RAGFlow(api_key=ragflow_api_key, 
                     base_url=ragflow_address)

assistant = rag_object.list_chats(id=chat_id)
assistant = assistant[0]
session = assistant.create_session(name="test_session1234")

print(session.messages[0]['content'])

question="請介紹公司產品"
# while True:
#     question = input("\n==================== User =====================\n> ")
#     print("\n==================== Miss R =====================\n")
    

response = ""
for ans in session.ask(question, stream=True):
    # 使用 chat_utils 處理內容
    print(ans.content[len(response):], end='', flush=True)
    response = ans.content

