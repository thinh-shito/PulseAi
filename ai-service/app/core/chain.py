"""
LLM Chain Initialization Module.
Initializes the LLM instance once and exports it for reuse across the application.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import settings

load_dotenv()

extraction_chain = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

llm_deepseek = ChatOpenAI(
    model="deepseek-v4-flash-free",               # <--- Thay đổi sang DeepSeek
    openai_api_key=os.getenv("OPENCODE_API_KEY"),
    openai_api_base="https://opencode.ai"
)

chat_agent_llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
