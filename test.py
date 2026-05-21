import os

# MiniMax API 配置
os.environ["MINIMAX_API_KEY"] = "sk-cp-Bb6N9rVp6LHY76AK1iU2QSBYLO1P_Y60n-eJAcz_bCOZ9_B9mDYRyrTwghmz_1KNTV0zomxKUEd0nL3NLeONErFofrHU4xFDBm2-j5djuhW_3K6T-71zEvY"
os.environ["MINIMAX_GROUP_ID"] = "2031708281008820704"  # 可选，部分接口需要

from langchain.chat_models import init_chat_model

# 使用 init_chat_model 初始化 MiniMax Chat模型
llm = init_chat_model(
    model="MiniMax-M2.7",  # MiniMax 模型名称
    model_provider="anthropic",
    api_key=os.environ["MINIMAX_API_KEY"],
    base_url="https://api.minimaxi.com/anthropic",
)

# 调用
from langchain_core.messages import HumanMessage

response = llm.invoke([HumanMessage(content="Hello, who are you?")])
print(response.content)

