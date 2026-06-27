"""
LLM Chain Initialization Module.
Initializes the LLM instance once and exports it for reuse across the application.
"""
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

extraction_chain = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
chat_chain = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)